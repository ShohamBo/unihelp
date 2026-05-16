import logging

from rest_framework.response import Response
from rest_framework.views import APIView

from programs.views import ScraperTokenPermission
from reviews.models import ReviewSnippet, ReviewSource, ProgramReviewLink

logger = logging.getLogger("maslul.reviews.api")


class ReviewSnippetBulkView(APIView):
    """
    POST /api/reviews/snippets/bulk/
    Accepts a list of Review dicts from the scraper layer.
    Bulk-upserts ReviewSnippet rows then runs ProgramMapper linking.
    """

    permission_classes = [ScraperTokenPermission]

    def post(self, request):
        items = request.data
        if not isinstance(items, list):
            return Response({"error": "expected a JSON array"}, status=400)

        from core.db_utils import bulk_upsert
        from django.utils.dateparse import parse_datetime

        # Pre-fetch / auto-create all ReviewSource rows in batch
        source_slugs = {i.get("source_slug", "").strip() for i in items if i.get("source_slug", "").strip()}
        sources = {}
        for slug in source_slugs:
            src, _ = ReviewSource.objects.get_or_create(
                name=slug, defaults={"base_url": "", "is_active": True}
            )
            sources[slug] = src

        objs = []
        skipped = 0
        for item in items:
            slug = item.get("source_slug", "").strip()
            ext_id = item.get("source_id", "").strip()
            if not slug or not ext_id or slug not in sources:
                skipped += 1
                continue
            objs.append(ReviewSnippet(
                source=sources[slug],
                external_id=ext_id,
                source_url=item.get("source_url", ""),
                raw_text=item.get("raw_text", ""),
                language=item.get("language", "he"),
                posted_at=parse_datetime(item["posted_at"]) if item.get("posted_at") else None,
                author_handle=item.get("author_handle", ""),
                metadata=item.get("metadata", {}),
            ))

        created, updated = bulk_upsert(
            ReviewSnippet,
            objs,
            unique_fields=["source", "external_id"],
            update_fields=["source_url", "raw_text", "language", "posted_at", "author_handle", "metadata"],
        )

        # Program linking — resolve degree_id for items that have one
        self._link_programs(items, sources)

        return Response({"saved": created, "updated": updated, "skipped": skipped})

    def _link_programs(self, items: list, sources: dict) -> None:
        for item in items:
            degree_id = item.get("degree_id", "").strip()
            if not degree_id:
                continue
            slug = item.get("source_slug", "").strip()
            ext_id = item.get("source_id", "").strip()
            if not slug or not ext_id:
                continue
            snippet = ReviewSnippet.objects.filter(
                source__name=slug, external_id=ext_id
            ).first()
            if not snippet:
                continue
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
