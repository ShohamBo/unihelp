import json
import logging

from celery import shared_task
from anthropic import Anthropic

logger = logging.getLogger("maslul.reviews.tasks")

ANALYSIS_MODEL = "claude-haiku-4-5-20251001"
SUMMARY_MODEL = "claude-sonnet-4-6"
MIN_SNIPPET_LENGTH = 30
MIN_SNIPPETS_FOR_SUMMARY = 3

THEME_CHOICES = [
    "workload", "professor_quality", "content_relevance", "job_prospects",
    "social_atmosphere", "admin_quality", "exam_difficulty", "grading_fairness",
    "facilities", "location", "value_for_money", "prestige",
]

_anthropic = Anthropic()


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def analyze_snippet(self, snippet_id: int):
    """
    Stage A: Per-snippet analysis (Phase 15).
    Calls Claude Haiku to extract sentiment, themes, and a Hebrew summary.
    Stores result in ReviewAnalysis. On success, queues summary regeneration
    for all programs linked to this snippet.
    """
    from reviews.models import ReviewSnippet, ReviewAnalysis

    try:
        snippet = ReviewSnippet.objects.get(id=snippet_id)
    except ReviewSnippet.DoesNotExist:
        return

    if ReviewAnalysis.objects.filter(snippet=snippet).exists():
        return  # already analyzed

    if len(snippet.raw_text) < MIN_SNIPPET_LENGTH:
        logger.debug(f"Snippet {snippet_id} too short, skipping")
        return

    try:
        response = _anthropic.messages.create(
            model=ANALYSIS_MODEL,
            max_tokens=512,
            messages=[{
                "role": "user",
                "content": (
                    "Analyze this student review about a university program in Israel.\n"
                    "Return a JSON object with exactly these fields:\n"
                    '- "sentiment": float from -1.0 (very negative) to 1.0 (very positive)\n'
                    f'- "themes": list chosen from: {", ".join(THEME_CHOICES)}\n'
                    '- "summary_he": one sentence in Hebrew summarizing the review (20-40 words)\n\n'
                    f"Review:\n{snippet.raw_text[:2000]}\n\n"
                    "Return only valid JSON, no markdown fences."
                ),
            }],
        )

        raw = response.content[0].text.strip()
        # Strip markdown fences if the model added them despite instructions
        if raw.startswith("```"):
            raw = raw.split("```")[1].lstrip("json").strip()

        data = json.loads(raw)

        ReviewAnalysis.objects.update_or_create(
            snippet=snippet,
            defaults={
                "sentiment": max(-1.0, min(1.0, float(data.get("sentiment", 0.0)))),
                "themes": [t for t in data.get("themes", []) if t in THEME_CHOICES],
                "summary_he": str(data.get("summary_he", ""))[:500],
                "model_version": ANALYSIS_MODEL,
            },
        )

        # Queue summary regen for each program linked to this snippet
        for link in snippet.program_links.values_list("program_id", flat=True):
            regenerate_program_summary.delay(link)

        logger.info(f"Analyzed snippet {snippet_id}: sentiment={data.get('sentiment')}")

    except json.JSONDecodeError as e:
        logger.error(f"Bad JSON from Haiku for snippet {snippet_id}: {e}")
    except Exception as e:
        logger.error(f"Failed to analyze snippet {snippet_id}: {e}", exc_info=True)
        raise self.retry(exc=e)


@shared_task(bind=True, max_retries=2, default_retry_delay=300)
def regenerate_program_summary(self, program_id: int):
    """
    Stage B: Per-program aggregation (Phase 15).
    Pulls the 100 most recent+confident analyzed snippets and calls Claude Sonnet
    to produce a Hebrew summary, pros/cons, and theme score breakdown.
    Stores result in ProgramSummary.
    """
    from programs.models import Program
    from reviews.models import ProgramReviewLink, ProgramSummary

    try:
        program = Program.objects.get(id=program_id)
    except Program.DoesNotExist:
        return

    links = (
        ProgramReviewLink.objects
        .filter(program=program)
        .select_related("snippet__analysis")
        .order_by("-confidence", "-snippet__posted_at")[:100]
    )

    analyzed = [
        link.snippet for link in links
        if hasattr(link.snippet, "analysis") and len(link.snippet.raw_text) >= MIN_SNIPPET_LENGTH
    ]

    if len(analyzed) < MIN_SNIPPETS_FOR_SUMMARY:
        logger.info(f"Program {program_id} has <{MIN_SNIPPETS_FOR_SUMMARY} analyzed snippets, skipping")
        return

    snippets_block = "\n---\n".join(s.raw_text[:500] for s in analyzed)

    try:
        response = _anthropic.messages.create(
            model=SUMMARY_MODEL,
            max_tokens=1500,
            messages=[{
                "role": "user",
                "content": (
                    f'Summarize student reviews for "{program.name_he}" at {program.institution_slug}.\n\n'
                    "Based ONLY on the reviews below, return a JSON object with:\n"
                    '- "summary_he": balanced ~200-word summary in Hebrew\n'
                    '- "pros_he": list of exactly 5 pros in Hebrew (one sentence each)\n'
                    '- "cons_he": list of exactly 5 cons in Hebrew (one sentence each)\n'
                    '- "themes_breakdown": object mapping theme keys to 0.0–1.0 scores\n'
                    f"  Available themes: {', '.join(THEME_CHOICES)}\n\n"
                    "IMPORTANT: Only summarize what students said. Do not invent facts.\n\n"
                    f"Reviews:\n{snippets_block[:8000]}\n\n"
                    "Return only valid JSON, no markdown fences."
                ),
            }],
        )

        raw = response.content[0].text.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1].lstrip("json").strip()

        data = json.loads(raw)

        ProgramSummary.objects.update_or_create(
            program=program,
            defaults={
                "summary_he": str(data.get("summary_he", ""))[:3000],
                "pros_he": list(data.get("pros_he", []))[:5],
                "cons_he": list(data.get("cons_he", []))[:5],
                "themes_breakdown": {
                    k: max(0.0, min(1.0, float(v)))
                    for k, v in data.get("themes_breakdown", {}).items()
                    if k in THEME_CHOICES
                },
                "snippet_count": len(analyzed),
            },
        )
        logger.info(f"Regenerated summary for program {program_id} using {len(analyzed)} snippets")

    except json.JSONDecodeError as e:
        logger.error(f"Bad JSON from Sonnet for program {program_id}: {e}")
    except Exception as e:
        logger.error(f"Failed to regenerate summary for program {program_id}: {e}", exc_info=True)
        raise self.retry(exc=e)


@shared_task
def sweep_unanalyzed_snippets():
    """
    Scheduled sweep: queue analyze_snippet for any snippet that has no ReviewAnalysis yet.
    Runs periodically to catch snippets that were saved without triggering the signal.
    """
    from reviews.models import ReviewSnippet, ReviewAnalysis

    analyzed_ids = ReviewAnalysis.objects.values_list("snippet_id", flat=True)
    pending = (
        ReviewSnippet.objects
        .exclude(id__in=analyzed_ids)
        .values_list("id", flat=True)[:500]
    )
    count = 0
    for sid in pending:
        analyze_snippet.delay(sid)
        count += 1
    logger.info(f"Queued {count} snippets for analysis")
    return count


@shared_task
def sweep_stale_summaries():
    """
    Scheduled sweep: regenerate summaries for programs whose summary is >7 days old
    or have no summary yet.
    """
    from datetime import timedelta
    from django.db.models import Q
    from django.utils import timezone
    from programs.models import Program

    cutoff = timezone.now() - timedelta(days=7)
    stale_ids = (
        Program.objects
        .filter(Q(summary__last_generated_at__lt=cutoff) | Q(summary__isnull=True))
        .values_list("id", flat=True)[:200]
    )

    count = 0
    for pid in stale_ids:
        regenerate_program_summary.delay(pid)
        count += 1
    logger.info(f"Queued {count} programs for summary regeneration")
    return count
