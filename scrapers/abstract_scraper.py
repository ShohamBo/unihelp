import asyncio
import hashlib
import os
import re
import sys
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin

import yaml
from bs4 import BeautifulSoup
from fake_useragent import UserAgent

from .common.async_request_client import AsyncRequestClient, ClientErrorException, RequestType
from .common.logger_manager import scraper_logger
from .db_tool import BeautifulTools
from .proxy import get_default_proxy
from .consts import SCRAPER_CONFIG_FILENAME, BS4_HTML_PARSER, DEGREE_LEVEL_NORMALIZER
from .models import ScraperConfig, PageContext, ScraperResult, Degree, Course, Review


class AbstractScraper(ABC):
    """Async base scraper for all Maslul scrapers.

    Adapted from the user's original abstract_scraper.py:
    - config_dir auto-detected via __init_subclass__ from the subclass's file location
    - config.yaml per scraper, loaded via load_scraper_config()
    - run() = _scrape() + _persist_result() — complete pipeline
    - All shared utilities live here: slugify, date parse, source_id, degree normalizer,
      CSS extraction, English→Hebrew translation, logger, DB client

    Concrete scrapers implement only:
      source_slug: str          (class variable)
      get_subpages(soup, url)   (discovery)
      parse_page(ctx)           (extraction → Degree | Course | Review)
    """

    source_slug: str
    config_dir: Path

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        try:
            module = sys.modules[cls.__module__]
            cls.config_dir = Path(module.__file__).parent
        except (KeyError, AttributeError):
            cls.config_dir = Path(".")

    def __init__(self, proxy: str | None = None):
        self.logger = scraper_logger.get_child(self.source_slug)
        self._ua = UserAgent()
        self.scraper_config = self.load_scraper_config()
        self.request_client = AsyncRequestClient(
            rate_limit=self.scraper_config.rate_limit,
            proxy=proxy or self.scraper_config.proxy or get_default_proxy(),
            logger=self.logger,
            retries=self.scraper_config.retries,
        )
        self._db = BeautifulTools(db_url=os.environ["DATABASE_URL"], logger=self.logger)

    # ------------------------------------------------------------------ config

    @classmethod
    def load_scraper_config(cls) -> ScraperConfig:
        config_path = cls.config_dir / SCRAPER_CONFIG_FILENAME
        raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))
        return ScraperConfig(**raw)

    # ----------------------------------------------------------------- headers

    @property
    def request_headers(self) -> dict:
        return {"User-Agent": self._ua.random}

    # ----------------------------------------------------------- HTTP + soup

    @staticmethod
    def soupify(html: str) -> BeautifulSoup:
        return BeautifulSoup(html, features=BS4_HTML_PARSER)

    async def get_page_soup(self, url: str) -> BeautifulSoup:
        html = await self.request_client.send_request(
            url, request_type=RequestType.GET, headers=self.request_headers
        )
        return self.soupify(html)

    # ----------------------------------------------- shared static utilities

    @staticmethod
    def _slugify(text: str) -> str:
        """Transliterate Hebrew+ASCII text to a URL-safe ASCII slug."""
        he_to_en = {
            "א": "a", "ב": "b", "ג": "g", "ד": "d", "ה": "h", "ו": "v",
            "ז": "z", "ח": "ch", "ט": "t", "י": "y", "כ": "k", "ך": "k",
            "ל": "l", "מ": "m", "ם": "m", "נ": "n", "ן": "n", "ס": "s",
            "ע": "a", "פ": "p", "ף": "p", "צ": "ts", "ץ": "ts", "ק": "k",
            "ר": "r", "ש": "sh", "ת": "t",
        }
        result = ""
        for char in text.lower():
            if char in he_to_en:
                result += he_to_en[char]
            elif char.isascii() and char.isalnum():
                result += char
            elif char in (" ", "-", "_"):
                result += "-"
        return re.sub(r"-+", "-", result).strip("-")[:80]

    @staticmethod
    def _extract_text_by_selectors(
        el: BeautifulSoup,
        selectors: list[str],
        attr: str | None = None,
    ) -> str:
        """Try each CSS selector in order; return first non-empty match.
        If attr is given, prefer that HTML attribute value over element text."""
        for sel in selectors:
            found = el.select_one(sel)
            if found:
                if attr:
                    return found.get(attr) or found.get_text(strip=True)
                return found.get_text(strip=True)
        return ""

    @staticmethod
    def _parse_date(date_str: str) -> datetime | None:
        if not date_str:
            return None
        for fmt in ["%Y-%m-%dT%H:%M:%S", "%Y-%m-%d", "%d/%m/%Y", "%d.%m.%Y", "%B %Y", "%Y"]:
            try:
                return datetime.strptime(date_str.strip(), fmt)
            except ValueError:
                continue
        return None

    @staticmethod
    def _url_to_slug(url: str) -> str:
        segment = url.rstrip("/").split("/")[-1]
        return re.sub(r"[^a-zA-Z0-9א-ת]", "-", segment)[:80]

    @staticmethod
    def generate_source_id(url: str, index: int, text: str) -> str:
        """Stable, dedup-safe id for a scraped item at (url, position, text)."""
        segment = url.rstrip("/").split("/")[-1]
        url_key = re.sub(r"[^a-zA-Z0-9א-ת]", "-", segment)[:80]
        return hashlib.md5(f"{url_key}:{index}:{text[:60]}".encode()).hexdigest()

    @staticmethod
    def _normalize_degree(raw: str) -> str:
        raw_lower = raw.lower()
        for key, level in DEGREE_LEVEL_NORMALIZER.items():
            if key in raw_lower:
                return level
        return "ba"

    # -------------------------------------------- error handling

    def handle_request_client_error(self, e: ClientErrorException) -> None:
        self.logger.warning(f"Client error {e.http_code} — skipping page")

    # -------------------------------------------- abstract interface

    @abstractmethod
    async def get_subpages(self, soup: BeautifulSoup, directory_url: str) -> list[str]:
        """Given a directory page soup, return all subpage URLs to scrape."""

    @abstractmethod
    async def parse_page(self, ctx: PageContext) -> list[Degree | Course | Review]:
        """Given a page context, return structured Degree/Course/Review objects."""

    # -------------------------------------------- scrape orchestration

    async def handle_single_page(self, url: str) -> list[Degree | Course | Review]:
        try:
            soup = await self.get_page_soup(url)
            ctx = PageContext(url=url, html_soup=soup)
            return await self.parse_page(ctx)
        except ClientErrorException as e:
            self.handle_request_client_error(e)
            return []
        except Exception as e:
            self.logger.error(f"Failed to handle page {url}: {e}", exc_info=True)
            return []

    async def scrape_directory(self, dir_route: str) -> list[Degree | Course | Review]:
        results: list[Degree | Course | Review] = []
        try:
            url = urljoin(self.scraper_config.base_url, dir_route)
            self.logger.info(f"Scraping directory {url}")
            soup = await self.get_page_soup(url)
            subpage_urls = await self.get_subpages(soup, url)
            self.logger.info(f"Found {len(subpage_urls)} subpages under {url}")
            page_results = await asyncio.gather(
                *[self.handle_single_page(sub_url) for sub_url in subpage_urls]
            )
            for items in page_results:
                results.extend(items)
        except ClientErrorException as e:
            self.handle_request_client_error(e)
        except Exception as e:
            self.logger.error(f"Critical error scraping directory {dir_route}: {e}", exc_info=True)
        return results

    async def _scrape(self) -> ScraperResult:
        """HTTP-based scrape over configured directories. Override for non-HTTP sources."""
        result = ScraperResult(source_slug=self.source_slug)
        async with self.request_client:
            dir_results = await asyncio.gather(
                *[self.scrape_directory(d) for d in self.scraper_config.directories]
            )
            for items in dir_results:
                for item in items:
                    if isinstance(item, Degree):
                        result.degrees.append(item)
                    elif isinstance(item, Course):
                        result.courses.append(item)
                    elif isinstance(item, Review):
                        result.reviews.append(item)
        return result

    async def _persist_result(self, result: ScraperResult) -> None:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._persist_sync, result)

    def _persist_sync(self, result: ScraperResult) -> None:
        """Write ScraperResult directly to the Django-managed PostgreSQL tables."""
        now = datetime.now(timezone.utc)
        db = self._db
        # 1. Upsert programs_program — institution_slug and faculty_slug stored directly
        program_rows = []
        for d in result.degrees:
            program_rows.append({
                "institution_slug": d.institution_slug,
                "faculty_slug": d.faculty_slug or "",
                "slug": d.slug,
                "name_he": d.name_he,
                "name_en": d.name_en,
                "degree_level": d.degree_level,
                "duration_years": d.duration_years,
                "total_credits": d.total_credits,
                "is_dual_major": d.is_dual_major,
                "is_extended": d.is_extended,
                "description_he": d.description_he,
                "canonical_url": d.canonical_url,
                "last_scraped_at": now,
                "metadata": d.metadata,
            })
        db.upsert_many_dicts(
            "programs_program",
            program_rows,
            conflict_cols=["institution_slug", "slug"],
            update_fields=[
                "faculty_slug", "name_he", "name_en", "degree_level", "duration_years",
                "total_credits", "is_dual_major", "is_extended", "description_he",
                "canonical_url", "last_scraped_at", "metadata",
            ],
        )

        # 2. Build (institution_slug, degree_slug) → program_id for course FK
        program_id_map: dict[tuple[str, str], int] = {}
        for d in result.degrees:
            pid = db.get_program_id_by_slugs(d.institution_slug, d.slug)
            if pid:
                program_id_map[(d.institution_slug, d.slug)] = pid

        # 3. Upsert programs_course
        course_rows = []
        for c in result.courses:
            program_id = program_id_map.get((c.institution_slug, c.degree_id))
            if program_id is None:
                self.logger.warning(f"Course skipped — ({c.institution_slug!r}, {c.degree_id!r}) not in program_id_map")
                continue
            course_rows.append({
                "program_id": program_id,
                "institution_slug": c.institution_slug,
                "name_he": c.name_he,
                "name_en": c.name_en,
                "course_code": c.course_code,
                "credits": c.credits,
                "semester": c.semester,
                "is_mandatory": c.is_mandatory,
                "description_he": c.description_he,
                "metadata": c.metadata,
            })
        coded = [r for r in course_rows if r["course_code"]]
        uncoded = [r for r in course_rows if not r["course_code"]]
        if coded:
            db.upsert_many_dicts(
                "programs_course",
                coded,
                conflict_cols=["program_id", "course_code"],
                conflict_where="course_code > ''",
                update_fields=["name_he", "name_en", "credits", "semester", "is_mandatory",
                               "description_he", "metadata"],
            )
        if uncoded:
            db.upsert_many_dicts(
                "programs_course",
                uncoded,
                conflict_cols=["program_id", "name_he"],
                update_fields=["credits", "semester", "is_mandatory", "description_he", "metadata"],
            )

        # 4. Upsert reviews_reviewsnippet — source_slug stored directly, no FK lookup
        # scraped_at is auto_now_add in Django (no DB default) — must supply it explicitly
        review_rows = []
        for r in result.reviews:
            review_rows.append({
                "source_slug": r.source_slug,
                "source_url": r.source_url,
                "external_id": r.source_id,
                "raw_text": r.raw_text,
                "language": r.language,
                "posted_at": r.posted_at,
                "scraped_at": now,
                "author_handle": r.author_handle,
                "metadata": r.metadata,
            })
        db.upsert_many_dicts(
            "reviews_reviewsnippet",
            review_rows,
            conflict_cols=["source_slug", "external_id"],
            update_fields=["raw_text", "language", "posted_at", "author_handle", "metadata"],
        )

        self.logger.info(
            f"[{self.source_slug}] persisted: "
            f"{len(program_rows)} programs, {len(course_rows)} courses, {len(review_rows)} reviews"
        )

    async def run(self) -> ScraperResult:
        """Entry point: scrape all sources then persist to Django. Returns ScraperResult."""
        self.logger.info(f"Starting scraper: {self.source_slug}")
        result = await self._scrape()
        self.logger.info(
            f"Scraped {self.source_slug}: "
            f"{len(result.degrees)} degrees, {len(result.courses)} courses, {len(result.reviews)} reviews"
        )
        await self._persist_result(result)
        return result
