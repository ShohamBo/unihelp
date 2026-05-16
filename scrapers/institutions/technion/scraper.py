from bs4 import BeautifulSoup

from ...abstract_scraper import AbstractScraper
from ...models import PageContext, Degree, Course, Review, ScraperResult
from .consts import (
    SOURCE_SLUG, INSTITUTION_SLUG,
    FACULTY_UNDERGRADUATE_URLS, PROGRAM_NAME_SELECTORS,
    FACULTY_NAME_SELECTORS, DEGREE_LEVEL_SELECTORS,
    DUAL_MAJOR_KEYWORDS, EXTENDED_KEYWORD,
)


class TechnionScraper(AbstractScraper):
    """
    Scrapes Technion degree programs from individual faculty subdomain pages.
    No central catalog — uses hardcoded FACULTY_UNDERGRADUATE_URLS list.
    Overrides _scrape() to iterate faculty URLs directly.
    """

    source_slug = SOURCE_SLUG

    async def get_subpages(self, soup: BeautifulSoup, directory_url: str) -> list[str]:
        return []

    async def parse_page(self, ctx: PageContext) -> list[Degree | Course | Review]:
        soup = ctx.html_soup
        faculty_name = self._extract_text_by_selectors(soup, FACULTY_NAME_SELECTORS)
        faculty_slug = self._slugify(faculty_name) if faculty_name else self._url_to_slug(ctx.url)

        degrees: list[Degree] = []
        for prog_el in soup.select("h2, .program-item, .degree-item, li.program"):
            name_he = prog_el.get_text(strip=True)
            if not name_he or len(name_he) < 5:
                continue
            slug = self._slugify(name_he)
            if not slug:
                continue
            degree_raw = self._extract_text_by_selectors(prog_el, DEGREE_LEVEL_SELECTORS)
            degrees.append(Degree(
                institution_slug=INSTITUTION_SLUG,
                slug=slug,
                name_he=name_he,
                faculty_slug=faculty_slug,
                degree_level=self._normalize_degree(degree_raw or "ba"),
                is_dual_major=any(kw in name_he for kw in DUAL_MAJOR_KEYWORDS),
                is_extended=EXTENDED_KEYWORD in name_he,
                canonical_url=ctx.url,
                metadata={"faculty_name": faculty_name},
                source_slug=self.source_slug,
            ))

        if not degrees and faculty_name:
            slug = self._slugify(faculty_name)
            if slug:
                degrees.append(Degree(
                    institution_slug=INSTITUTION_SLUG,
                    slug=slug,
                    name_he=faculty_name,
                    faculty_slug=faculty_slug,
                    degree_level="ba",
                    canonical_url=ctx.url,
                    metadata={},
                    source_slug=self.source_slug,
                ))
        return degrees

    async def _scrape(self) -> ScraperResult:
        result = ScraperResult(source_slug=self.source_slug)
        async with self.request_client:
            for url in FACULTY_UNDERGRADUATE_URLS:
                items = await self.handle_single_page(url)
                for item in items:
                    if isinstance(item, Degree):
                        result.degrees.append(item)
        return result
