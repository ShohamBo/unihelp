from urllib.parse import urljoin

from bs4 import BeautifulSoup

from ..abstract_scraper import AbstractScraper
from ..models import PageContext, Degree, Course, Review
from .consts import (
    SOURCE_SLUG, INSTITUTION_SLUG, BASE_URL,
    PROGRAM_SELECTORS, FACULTY_NAME_SELECTORS, DEGREE_LEVEL_SELECTORS,
    FACULTY_LINK_KEYWORDS, DUAL_MAJOR_KEYWORDS, EXTENDED_KEYWORD,
)


class TauScraper(AbstractScraper):
    """
    Scrapes the TAU program catalog.
    Directory (/he/faculties) → faculty pages → Degree objects per page.
    Note: targets static program listing pages, not the ViewState-gated Yedion catalog.
    """

    source_slug = SOURCE_SLUG

    async def get_subpages(self, soup: BeautifulSoup, directory_url: str) -> list[str]:
        seen: set[str] = set()
        urls: list[str] = []
        for link in soup.select("a[href]"):
            href = link.get("href", "")
            if not href or href in seen:
                continue
            if any(kw in href.lower() for kw in FACULTY_LINK_KEYWORDS):
                full = href if href.startswith("http") else urljoin(BASE_URL, href)
                seen.add(full)
                urls.append(full)
        return urls

    async def parse_page(self, ctx: PageContext) -> list[Degree | Course | Review]:
        soup: BeautifulSoup = ctx.html_soup
        faculty_name = self._extract_text_by_selectors(soup, FACULTY_NAME_SELECTORS)
        faculty_slug = self._slugify(faculty_name)
        degrees: list[Degree] = []

        for program_el in soup.select(", ".join(PROGRAM_SELECTORS)):
            name_el = program_el.select_one("a, .program-name, td:first-child")
            if not name_el:
                continue

            name_he = name_el.get_text(strip=True)
            if not name_he:
                continue

            slug = self._slugify(name_he)
            if not slug:
                continue

            prog_url = name_el.get("href", "")
            if prog_url and not prog_url.startswith("http"):
                prog_url = urljoin(ctx.url, prog_url)

            degree_raw = self._extract_text_by_selectors(program_el, DEGREE_LEVEL_SELECTORS)

            degrees.append(Degree(
                institution_slug=INSTITUTION_SLUG,
                slug=slug,
                name_he=name_he,
                faculty_slug=faculty_slug,
                degree_level=self._normalize_degree(degree_raw),
                is_dual_major=any(kw in name_he for kw in DUAL_MAJOR_KEYWORDS),
                is_extended=EXTENDED_KEYWORD in name_he,
                canonical_url=prog_url,
                metadata={"source_faculty_name": faculty_name},
                source_slug=self.source_slug,
            ))

        return degrees
