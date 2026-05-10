import asyncio
import logging
import sys
from abc import ABC, abstractmethod
from pathlib import Path
from typing import AsyncIterator

from bs4 import BeautifulSoup
from fake_useragent import UserAgent

from .common.async_request_client import AsyncRequestClient, ClientErrorException, RequestType
from .models import ReviewSnippetData, ProgramData

BS4_PARSER = "html.parser"


class BaseScraper(ABC):
    """
    Async base scraper for the Maslul platform — adapted from the Israeli exam
    scraper infrastructure. All scrapers (review + program catalog) inherit here.

    Key difference from original: outputs ReviewSnippetData/ProgramData structs
    instead of writing binary blobs to S3. Persistence is handled by Django API
    via the Celery task layer (scrapers/tasks.py).
    """

    source_slug: str
    requires_browser: bool = False
    requires_proxy: bool = False
    rate_limit_per_minute: float = 10.0
    config_dir: Path

    def __init_subclass__(cls):
        super().__init_subclass__()
        try:
            module = sys.modules[cls.__module__]
            cls.config_dir = Path(module.__file__).parent
        except (KeyError, AttributeError):
            cls.config_dir = Path(".")

    def __init__(self, proxy: str | None = None):
        self.logger = logging.getLogger(f"maslul.scrapers.{self.source_slug}")
        self._ua = UserAgent()
        self._current_ua = self._ua.random
        rate_per_second = self.rate_limit_per_minute / 60.0
        self.request_client = AsyncRequestClient(
            rate_limit=rate_per_second,
            proxy=proxy,
            logger=self.logger,
        )
        self._failed = 0

    @property
    def request_headers(self) -> dict:
        return {"User-Agent": self._current_ua}

    def rotate_useragent(self):
        self._current_ua = self._ua.random

    @staticmethod
    def soupify(html: str) -> BeautifulSoup:
        return BeautifulSoup(html, BS4_PARSER)

    async def get_page_html(self, url: str) -> str:
        return await self.request_client.send_request(
            url, request_type=RequestType.GET, headers=self.request_headers
        )

    async def get_page_soup(self, url: str) -> BeautifulSoup:
        html = await self.get_page_html(url)
        return self.soupify(html)

    @abstractmethod
    async def discover_urls(self) -> AsyncIterator[str]:
        """Yield all URLs to scrape. May make HTTP calls to enumerate pages."""
        ...

    @abstractmethod
    async def scrape_url(self, url: str) -> dict:
        """Fetch and parse a single URL. Return structured raw dict."""
        ...

    @abstractmethod
    def to_review_snippets(self, raw: dict) -> list[ReviewSnippetData]:
        """Transform raw dict into ReviewSnippetData list. Pure, no I/O."""
        ...

    def handle_client_error(self, e: ClientErrorException, url: str):
        """Override to implement custom 4xx handling (proxy rotation, etc.)."""
        self.logger.error(f"Client error {e.http_code} for {url} — skipping")

    async def _handle_single_url(self, url: str) -> list[ReviewSnippetData]:
        try:
            self.logger.info(f"Scraping {url}")
            raw = await self.scrape_url(url)
            snippets = self.to_review_snippets(raw)
            self.logger.info(f"Got {len(snippets)} snippets from {url}")
            return snippets
        except ClientErrorException as e:
            self.handle_client_error(e, url)
            self._failed += 1
            return []
        except Exception as e:
            self.logger.error(f"Failed to scrape {url}: {e}", exc_info=True)
            self._failed += 1
            return []

    async def run(self) -> list[ReviewSnippetData]:
        """
        Entry point. Discovers all URLs, scrapes each concurrently,
        returns all extracted snippets. Persistence is the caller's job.
        """
        self.logger.info(f"Starting scraper: {self.source_slug}")
        all_snippets: list[ReviewSnippetData] = []

        async with self.request_client:
            urls = [url async for url in self.discover_urls()]
            self.logger.info(f"Discovered {len(urls)} URLs for {self.source_slug}")

            results = await asyncio.gather(*[self._handle_single_url(url) for url in urls])
            for snippets in results:
                all_snippets.extend(snippets)

        self.logger.info(
            f"Finished {self.source_slug}: {len(all_snippets)} snippets, {self._failed} failures"
        )
        return all_snippets


class BaseProgramScraper(BaseScraper):
    """Base for scrapers that extract program catalog data."""

    @abstractmethod
    def to_programs(self, raw: dict) -> list[ProgramData]:
        ...

    def to_review_snippets(self, raw: dict) -> list[ReviewSnippetData]:
        return []

    async def run_programs(self) -> list[ProgramData]:
        self.logger.info(f"Starting program scraper: {self.source_slug}")
        all_programs: list[ProgramData] = []

        async with self.request_client:
            urls = [url async for url in self.discover_urls()]
            self.logger.info(f"Discovered {len(urls)} program pages")

            for url in urls:
                try:
                    raw = await self.scrape_url(url)
                    programs = self.to_programs(raw)
                    all_programs.extend(programs)
                    self.logger.info(f"Got {len(programs)} programs from {url}")
                except Exception as e:
                    self.logger.error(f"Failed on {url}: {e}", exc_info=True)
                    self._failed += 1

        self.logger.info(f"Finished {self.source_slug}: {len(all_programs)} programs, {self._failed} failures")
        return all_programs
