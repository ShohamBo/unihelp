import logging
import os

from django.contrib.admin.views.decorators import staff_member_required
from django.db import models
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.utils.dateparse import parse_datetime
from rest_framework import generics
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import BasePermission

from core.db_utils import upsert_by_fields_conditional
from institutions.models import Institution, Faculty
from programs.models import Program, Course
from programs.serializers import ProgramListSerializer, ProgramDetailSerializer

logger = logging.getLogger("maslul.programs.api")

TIERS = ["exact", "fuzzy", "llm", "none", "cache_hit"]


class ScraperTokenPermission(BasePermission):
    """Allows requests that carry the BACKEND_API_TOKEN env-var token.
    If the env var is unset (dev), all requests are allowed."""

    def has_permission(self, request, view):
        expected = os.getenv("BACKEND_API_TOKEN", "")
        if not expected:
            return True
        auth = request.META.get("HTTP_AUTHORIZATION", "")
        if not auth.startswith("Token "):
            return False
        return auth[6:].strip() == expected


@staff_member_required
def mapper_stats(request):
    """Returns mapper hit counts per tier (Redis counters)."""
    from django.core.cache import cache

    stats = {}
    total = 0
    for tier in TIERS:
        count = int(cache.get(f"mapper_stats:{tier}") or 0)
        stats[tier] = count
        total += count

    for tier in TIERS:
        stats[f"{tier}_pct"] = round(stats[tier] / total * 100, 1) if total else 0.0

    stats["total"] = total
    return JsonResponse(stats)


class ProgramBulkView(APIView):
    """
    POST /api/programs/bulk/
    Accepts a list of Degree dicts from the scraper layer.
    Upserts each into Program; skips rows where institution_slug is unknown.
    """

    permission_classes = [ScraperTokenPermission]

    def post(self, request):
        items = request.data
        if not isinstance(items, list):
            return Response({"error": "expected a JSON array"}, status=400)

        from core.db_utils import bulk_upsert

        # Pre-fetch all referenced institutions in one query
        slugs = {i.get("institution_slug", "") for i in items if i.get("institution_slug")}
        institutions = {inst.slug: inst for inst in Institution.objects.filter(slug__in=slugs)}

        objs = []
        skipped = 0
        for item in items:
            inst = institutions.get(item.get("institution_slug", ""))
            if not inst:
                logger.warning(f"Unknown institution_slug: {item.get('institution_slug')!r} — skipping")
                skipped += 1
                continue
            slug = item.get("slug", "").strip()
            if not slug:
                skipped += 1
                continue

            faculty = None
            faculty_slug = item.get("faculty_slug", "").strip()
            if faculty_slug:
                faculty, _ = Faculty.objects.get_or_create(
                    institution=inst,
                    slug=faculty_slug,
                    defaults={"name_he": faculty_slug, "name_en": ""},
                )

            objs.append(Program(
                institution=inst,
                slug=slug,
                faculty=faculty,
                name_he=item.get("name_he", ""),
                name_en=item.get("name_en", ""),
                degree_level=item.get("degree_level", "ba"),
                duration_years=item.get("duration_years"),
                total_credits=item.get("total_credits"),
                is_dual_major=bool(item.get("is_dual_major", False)),
                is_extended=bool(item.get("is_extended", False)),
                description_he=item.get("description_he", ""),
                canonical_url=item.get("canonical_url", ""),
                metadata=item.get("metadata", {}),
            ))

        created, updated = bulk_upsert(
            Program,
            objs,
            unique_fields=["institution", "slug"],
            update_fields=[
                "faculty", "name_he", "name_en", "degree_level",
                "duration_years", "total_credits", "is_dual_major",
                "is_extended", "description_he", "canonical_url", "metadata",
            ],
        )
        return Response({"saved": created, "updated": updated, "skipped": skipped})


class CourseBulkView(APIView):
    """
    POST /api/programs/courses/bulk/
    Accepts a list of Course dicts from the scraper layer.
    Resolves program by institution_slug + degree_id (program slug).
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
                logger.exception(f"Failed to upsert course: {item.get('name_he')}")
                skipped_count += 1

        return Response({"saved": created_count, "updated": updated_count, "skipped": skipped_count})

    def _upsert(self, item: dict) -> str:
        institution_slug = item.get("institution_slug", "").strip()
        try:
            institution = Institution.objects.get(slug=institution_slug)
        except Institution.DoesNotExist:
            return "skipped"

        program = None
        degree_id = item.get("degree_id", "").strip()
        if degree_id:
            program = Program.objects.filter(institution=institution, slug=degree_id).first()

        name_he = item.get("name_he", "").strip()
        if not name_he:
            return "skipped"

        course_code = item.get("course_code", "").strip()
        update_fields = {
            "institution": institution,
            "name_he": name_he,
            "name_en": item.get("name_en", ""),
            "credits": item.get("credits"),
            "semester": item.get("semester", ""),
            "is_mandatory": bool(item.get("is_mandatory", True)),
            "description_he": item.get("description_he", ""),
            "metadata": item.get("metadata", {}),
        }

        if program and course_code:
            _, created = upsert_by_fields_conditional(
                Course,
                lookup_fields={"program": program, "course_code": course_code},
                update_fields=update_fields,
            )
        else:
            # No stable key — create only if not already present by name+program
            lookup = {"program": program, "name_he": name_he} if program else {"institution": institution, "name_he": name_he}
            _, created = upsert_by_fields_conditional(Course, lookup_fields=lookup, update_fields={
                k: v for k, v in update_fields.items() if k not in lookup
            })

        return "created" if created else "updated"


class ProgramListView(generics.ListAPIView):
    """GET /api/programs/?institution=tau&degree_level=ba&search=מדעי"""

    serializer_class = ProgramListSerializer

    def get_queryset(self):
        qs = Program.objects.select_related('institution', 'faculty')
        institution = self.request.query_params.get('institution', '').strip()
        degree_level = self.request.query_params.get('degree_level', '').strip()
        search = self.request.query_params.get('search', '').strip()

        if institution:
            qs = qs.filter(institution__slug=institution)
        if degree_level:
            qs = qs.filter(degree_level=degree_level)
        if search:
            qs = qs.filter(
                models.Q(name_he__icontains=search) | models.Q(name_en__icontains=search)
            )
        return qs.order_by('institution__name_he', 'name_he')


class ProgramDetailView(generics.RetrieveAPIView):
    """GET /api/programs/<institution>/<program>/"""

    serializer_class = ProgramDetailSerializer

    def get_object(self):
        return get_object_or_404(
            Program.objects
                   .select_related('institution', 'faculty', 'admission')
                   .prefetch_related('summary'),
            institution__slug=self.kwargs['institution'],
            slug=self.kwargs['program'],
        )
