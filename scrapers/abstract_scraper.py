import asyncio
import hashlib
import logging
import re
import sys
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin

import yaml
from anthropic import AsyncAnthropic
from bs4 import BeautifulSoup
from fake_useragent import UserAgent

from .common.async_request_client import AsyncRequestClient, ClientErrorException, RequestType
from .consts import (
    SCRAPER_CONFIG_FILENAME, BS4_HTML_PARSER, TRANSLATION_MODEL,
    HEBREW_CHAR_RATIO_THRESHOLD, DEGREE_LEVEL_NORMALIZER,
)
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
        self.logger = logging.getLogger(f"maslul.scrapers.{self.source_slug}")
        self._ua = UserAgent()
        self._anthropic = AsyncAnthropic()
        self.scraper_config = self.load_scraper_config()
        self.request_client = AsyncRequestClient(
            rate_limit=self.scraper_config.rate_limit,
            proxy=proxy or self.scraper_config.proxy,
            logger=self.logger,
            retries=self.scraper_config.retries,
        )
        # Import here to avoid circular import; django_client imports models
        from .django_client import DjangoApiClient
        self._db_client = DjangoApiClient()

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

    # -------------------------------------------------- Hebrew translation

    @staticmethod
    def _is_hebrew(text: str) -> bool:
        if not text:
            return False
        he_chars = sum(1 for c in text if "א" <= c <= "ת")
        return (he_chars / max(len(text), 1)) >= HEBREW_CHAR_RATIO_THRESHOLD

    async def translate_to_hebrew(self, text: str) -> str:
        """Translate to Hebrew via Claude Haiku. Returns as-is if already Hebrew or empty."""
        if not text or self._is_hebrew(text):
            return text
        try:
            msg = await self._anthropic.messages.create(
                model=TRANSLATION_MODEL,
                max_tokens=512,
                messages=[{
                    "role": "user",
                    "content": f"Translate the following to Hebrew. Return only the translation:\n\n{text}",
                }],
            )
            return msg.content[0].text.strip()
        except Exception as e:
            self.logger.warning(f"Translation failed, returning original: {e}")
            return text

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
        await self._db_client.save_scraped_result(result)

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
