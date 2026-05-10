import logging

from django.utils.dateparse import parse_datetime
from rest_framework.response import Response
from rest_framework.views import APIView

from core.db_utils import upsert_by_fields_conditional
from programs.views import ScraperTokenPermission
from reviews.models import ReviewSnippet, ReviewSource, ProgramReviewLink

logger = logging.getLogger("maslul.reviews.api")


class ReviewSnippetBulkView(APIView):
    """
    POST /api/reviews/snippets/bulk/
    Accepts a list of Review dicts from the scraper layer.
    Upserts each ReviewSnippet and runs ProgramMapper to create ProgramReviewLink.
    Auto-creates ReviewSource rows for unknown source_slugs.
    """

    permission_classes = [ScraperTokenPermission]

    def post(self, request):
        items = request.data
        if not isinstance(items, list):
            return Response({"error": "expected a JSON array"}, status=400)

        created_count = updated_count = skipped_count = 0

        for item in items:
            try:
                outcome = self._upsert(item)
                if outcome == "created":
                    created_count += 1
                elif outcome == "updated":
                    updated_count += 1
                else:
                    skipped_count += 1
            except Exception:
                logger.exception(f"Failed to upsert snippet: {item.get('source_id')}")
                skipped_count += 1

        return Response({"saved": created_count, "updated": updated_count, "skipped": skipped_count})

    def _upsert(self, item: dict) -> str:
        source_slug = item.get("source_slug", "").strip()
        if not source_slug:
            return "skipped"

        source, _ = ReviewSource.objects.get_or_create(
            name=source_slug,
            defaults={"base_url": "", "is_active": True},
        )

        external_id = item.get("source_id", "").strip()
        if not external_id:
            return "skipped"

        snippet, created = upsert_by_fields_conditional(
            ReviewSnippet,
            lookup_fields={"source": source, "external_id": external_id},
            update_fields={
                "source_url": item.get("source_url", ""),
                "raw_text": item.get("raw_text", ""),
                "language": item.get("language", "he"),
                "posted_at": parse_datetime(item["posted_at"]) if item.get("posted_at") else None,
                "author_handle": item.get("author_handle", ""),
                "metadata": item.get("metadata", {}),
            },
        )

        degree_id = item.get("degree_id", "").strip()
        if degree_id:
            self._link_program(snippet, degree_id)

        return "created" if created else "updated"

    def _link_program(self, snippet: ReviewSnippet, degree_id: str) -> None:
        try:
            from programs.mapper import program_mapper
            result = program_mapper.map_text(degree_id)
            if result.program:
                ProgramReviewLink.objects.update_or_create(
                    snippet=snippet,
                    program=result.program,
                    defaults={"confidence": result.confidence, "method": result.tier},
                )
        except Exception:
            logger.warning(f"ProgramMapper failed for degree_id={degree_id!r}", exc_info=True)
