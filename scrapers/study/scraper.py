from urllib.parse import urljoin

from bs4 import BeautifulSoup

from ..abstract_scraper import AbstractScraper
from ..models import PageContext, Degree, Course, Review
from .consts import (
    SOURCE_SLUG, BASE_URL, MIN_REVIEW_LENGTH, INSTITUTION_NAME_MAP,
    PROGRAM_LINK_SELECTORS, REVIEW_SELECTORS, REVIEW_TEXT_SELECTORS,
    REVIEW_DATE_SELECTORS, PROGRAM_NAME_SELECTORS, INSTITUTION_NAME_SELECTORS,
)


class StudyScraper(AbstractScraper):
    """
    Scrapes student reviews from study.co.il.
    Directory (/) → program pages → Review objects per page.
    degree_id is set to the slugified program name for later resolution by ProgramMapper.
    """

    source_slug = SOURCE_SLUG

    async def get_subpages(self, soup: BeautifulSoup, directory_url: str) -> list[str]:
        seen: set[str] = set()
        urls: list[str] = []
        for selector in PROGRAM_LINK_SELECTORS:
            for link in soup.select(selector):
                href = link.get("href", "")
                if not href:
                    continue
                full = href if href.startswith("http") else urljoin(BASE_URL, href)
                if full not in seen:
                    seen.add(full)
                    urls.append(full)
        return urls

    async def parse_page(self, ctx: PageContext) -> list[Degree | Course | Review]:
        soup: BeautifulSoup = ctx.html_soup

        program_name = await self.translate_to_hebrew(
            self._extract_text_by_selectors(soup, PROGRAM_NAME_SELECTORS)
        )
        degree_id = self._slugify(program_name) or self._url_to_slug(ctx.url)

        institution_text = self._extract_text_by_selectors(soup, INSTITUTION_NAME_SELECTORS)
        institution_slug = self._resolve_institution(institution_text)

        reviews: list[Review] = []
        for i, review_el in enumerate(soup.select(", ".join(REVIEW_SELECTORS))):
            raw_text = (
                self._extract_text_by_selectors(review_el, REVIEW_TEXT_SELECTORS)
                or review_el.get_text(strip=True)
            )
            if len(raw_text) < MIN_REVIEW_LENGTH:
                continue

            raw_text = await self.translate_to_hebrew(raw_text)
            date_str = self._extract_text_by_selectors(review_el, REVIEW_DATE_SELECTORS, attr="datetime")

            reviews.append(Review(
                degree_id=degree_id,
                source_slug=self.source_slug,
                source_url=ctx.url,
                source_id=self.generate_source_id(ctx.url, i, raw_text),
                raw_text=raw_text,
                language="he",
                posted_at=self._parse_date(date_str),
                metadata={"program_name": program_name, "institution_slug": institution_slug},
            ))

        return reviews

    @staticmethod
    def _resolve_institution(text: str) -> str:
        for display_name, slug in INSTITUTION_NAME_MAP.items():
            if display_name in text:
                return slug
        return ""
