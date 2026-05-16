from urllib.parse import urljoin

from bs4 import BeautifulSoup

from ...abstract_scraper import AbstractScraper
from ...models import PageContext, Degree, Course, Review
from .consts import (
    SOURCE_SLUG, INSTITUTION_SLUG, BASE_URL, PROGRAM_LINK_RE,
    PROGRAM_NAME_SELECTORS, FACULTY_NAME_SELECTORS, DEGREE_LEVEL_SELECTORS,
    DUAL_MAJOR_KEYWORDS, EXTENDED_KEYWORD,
)


class TauInstitutionScraper(AbstractScraper):
    """
    Scrapes TAU degree programs from go.tau.ac.il.
    Each directory is a faculty area page (e.g. /he/exact).
    get_subpages() collects individual program URLs (/he/{area}/ba/{slug}).
    parse_page() extracts one Degree per program page.
    """

    source_slug = SOURCE_SLUG

    async def get_subpages(self, soup: BeautifulSoup, directory_url: str) -> list[str]:
        seen: set[str] = set()
        urls: list[str] = []
        for link in soup.select("a[href]"):
            href = link.get("href", "")
            if not href or href in seen:
                continue
            if PROGRAM_LINK_RE.match(href):
                full = href if href.startswith("http") else urljoin(BASE_URL, href)
                seen.add(href)
                urls.append(full)
        return urls

    async def parse_page(self, ctx: PageContext) -> list[Degree | Course | Review]:
        soup = ctx.html_soup
        name_he = self._extract_text_by_selectors(soup, PROGRAM_NAME_SELECTORS)
        if not name_he:
            return []

        slug = self._slugify(name_he)
        if not slug:
            return []

        # Extract degree level and faculty from URL: /he/{faculty}/{ba|ma}/{slug}
        parts = ctx.url.rstrip("/").split("/")
        degree_level_raw = ""
        faculty_area = ""
        if len(parts) >= 2:
            degree_level_raw = parts[-2] if parts[-2] in ("ba", "ma") else ""
            faculty_area = parts[-3] if len(parts) >= 3 else ""

        if not degree_level_raw:
            degree_level_raw = self._extract_text_by_selectors(soup, DEGREE_LEVEL_SELECTORS)

        faculty_name = self._extract_text_by_selectors(soup, FACULTY_NAME_SELECTORS) or faculty_area
        faculty_slug = self._slugify(faculty_name) or faculty_area

        return [Degree(
            institution_slug=INSTITUTION_SLUG,
            slug=slug,
            name_he=name_he,
            faculty_slug=faculty_slug,
            degree_level=self._normalize_degree(degree_level_raw),
            is_dual_major=any(kw in name_he for kw in DUAL_MAJOR_KEYWORDS),
            is_extended=EXTENDED_KEYWORD in name_he,
            canonical_url=ctx.url,
            metadata={"faculty_area": faculty_area},
            source_slug=self.source_slug,
        )]
