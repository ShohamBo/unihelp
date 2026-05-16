import asyncio
import os
from dataclasses import asdict

import aiohttp

from .common.logger_manager import scraper_logger
from .models import Degree, Course, Review, ScraperResult

logger = scraper_logger.get_child("django_client")

BACKEND_API_URL = os.getenv("BACKEND_API_URL", "http://localhost:8000/api")
API_TOKEN = os.getenv("BACKEND_API_TOKEN", "")


class DjangoApiClient:
    """Posts scraped data to the Django backend REST API."""

    def __init__(self):
        self.base_url = BACKEND_API_URL.rstrip("/")
        self.headers = {
            "Authorization": f"Token {API_TOKEN}",
            "Content-Type": "application/json",
        }

    async def _post(self, path: str, payload: list[dict]) -> int:
        if not payload:
            return 0
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.base_url}{path}",
                json=payload,
                headers=self.headers,
            ) as resp:
                if resp.status not in (200, 201):
                    body = await resp.text()
                    logger.error(f"POST {path} failed: {resp.status} — {body[:200]}")
                    return 0
                result = await resp.json()
                saved = result.get("saved", len(payload))
                logger.info(f"POST {path}: saved {saved}/{len(payload)}")
                return saved

    async def save_degrees(self, degrees: list[Degree]) -> int:
        payload = [
            {
                "institution_slug": d.institution_slug,
                "slug": d.slug,
                "name_he": d.name_he,
                "name_en": d.name_en,
                "faculty_slug": d.faculty_slug,
                "degree_level": d.degree_level,
                "duration_years": d.duration_years,
                "total_credits": d.total_credits,
                "is_dual_major": d.is_dual_major,
                "is_extended": d.is_extended,
                "description_he": d.description_he,
                "canonical_url": d.canonical_url,
                "metadata": d.metadata,
                "source_slug": d.source_slug,
            }
            for d in degrees
        ]
        return await self._post("/programs/bulk/", payload)

    async def save_courses(self, courses: list[Course]) -> int:
        payload = [
            {
                "degree_id": c.degree_id,
                "institution_slug": c.institution_slug,
                "name_he": c.name_he,
                "name_en": c.name_en,
                "course_code": c.course_code,
                "credits": c.credits,
                "semester": c.semester,
                "is_mandatory": c.is_mandatory,
                "description_he": c.description_he,
                "metadata": c.metadata,
            }
            for c in courses
        ]
        return await self._post("/programs/courses/bulk/", payload)

    async def save_reviews(self, reviews: list[Review]) -> int:
        payload = [
            {
                "degree_id": r.degree_id,
                "source_slug": r.source_slug,
                "source_url": r.source_url,
                "source_id": r.source_id,
                "raw_text": r.raw_text,
                "language": r.language,
                "posted_at": r.posted_at.isoformat() if r.posted_at else None,
                "author_handle": r.author_handle,
                "metadata": r.metadata,
            }
            for r in reviews
        ]
        return await self._post("/reviews/snippets/bulk/", payload)

    async def save_scraped_result(self, result: ScraperResult) -> None:
        await asyncio.gather(
            self.save_degrees(result.degrees),
            self.save_courses(result.courses),
            self.save_reviews(result.reviews),
        )
