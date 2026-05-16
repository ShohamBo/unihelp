from urllib.parse import urljoin

from bs4 import BeautifulSoup

from ...abstract_scraper import AbstractScraper
from ...models import PageContext, Degree, Course, Review
from .consts import (
    SOURCE_SLUG, INSTITUTION_SLUG, BASE_URL,
    PROGRAM_LINK_SELECTORS, PROGRAM_NAME_SELECTORS,
    FACULTY_NAME_SELECTORS, DEGREE_LEVEL_SELECTORS,
    DUAL_MAJOR_KEYWORDS, EXTENDED_KEYWORD,
)


class BiuScraper(AbstractScraper):
    """Scrapes BIU programs from biu.ac.il/catalog/תואר ראשון."""

    source_slug = SOURCE_SLUG

    async def get_subpages(self, soup: BeautifulSoup, directory_url: str) -> list[str]:
        seen: set[str] = set()
        urls: list[str] = []
        for selector in PROGRAM_LINK_SELECTORS:
            for link in soup.select(selector):
                href = link.get("href", "")
                if not href or href == directory_url:
                    continue
                full = href if href.startswith("http") else urljoin(BASE_URL, href)
                if full not in seen:
                    seen.add(full)
                    urls.append(full)
        return urls

    async def parse_page(self, ctx: PageContext) -> list[Degree | Course | Review]:
        soup = ctx.html_soup
        name_he = self._extract_text_by_selectors(soup, PROGRAM_NAME_SELECTORS)
        if not name_he:
            return []

        slug = self._slugify(name_he) or self._url_to_slug(ctx.url)
        faculty_name = self._extract_text_by_selectors(soup, FACULTY_NAME_SELECTORS)
        faculty_slug = self._slugify(faculty_name) if faculty_name else ""
        degree_raw = self._extract_text_by_selectors(soup, DEGREE_LEVEL_SELECTORS)

        return [Degree(
            institution_slug=INSTITUTION_SLUG,
            slug=slug,
            name_he=name_he,
            faculty_slug=faculty_slug,
            degree_level=self._normalize_degree(degree_raw or "ba"),
            is_dual_major=any(kw in name_he for kw in DUAL_MAJOR_KEYWORDS),
            is_extended=EXTENDED_KEYWORD in name_he,
            canonical_url=ctx.url,
            metadata={},
            source_slug=self.source_slug,
        )]
