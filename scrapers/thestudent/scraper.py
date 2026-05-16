import re
from bs4 import BeautifulSoup

from ..abstract_scraper import AbstractScraper
from ..models import PageContext, Degree, Course, Review
from .consts import (
    SOURCE_SLUG, BASE_URL, MIN_REVIEW_LENGTH,
    REVIEW_SELECTORS, REVIEW_TEXT_SELECTORS, REVIEW_DATE_SELECTORS,
    REVIEW_AUTHOR_SELECTORS, PROGRAM_NAME_SELECTORS,
)

_CATEGORY_LINK_RE = re.compile(r"^/c\d+_")
_DEGREE_LINK_RE = re.compile(r"/Degrees/Degree_\d+", re.IGNORECASE)


class TheStudentScraper(AbstractScraper):
    """
    Scrapes student reviews from thestudent.co.il.
    3-level: /Categories → /c[N]_[name] category pages → /Degrees/Degree_[N].html
    get_subpages() does both hops so the base scrape_directory() sees only leaf URLs.
    """

    source_slug = SOURCE_SLUG

    async def get_subpages(self, soup: BeautifulSoup, directory_url: str) -> list[str]:
        seen: set[str] = set()
        degree_urls: list[str] = []

        category_urls: list[str] = []
        for link in soup.select("a[href]"):
            href = link.get("href", "")
            if _CATEGORY_LINK_RE.match(href):
                full = href if href.startswith("http") else f"{BASE_URL}{href}"
                if full not in seen:
                    seen.add(full)
                    category_urls.append(full)

        for cat_url in category_urls:
            try:
                cat_soup = await self.get_page_soup(cat_url)
                for link in cat_soup.select("a[href]"):
                    href = link.get("href", "")
                    if _DEGREE_LINK_RE.search(href):
                        full = href if href.startswith("http") else f"{BASE_URL}{href}"
                        if full not in seen:
                            seen.add(full)
                            degree_urls.append(full)
            except Exception:
                self.logger.warning(f"Failed to fetch category page {cat_url}")
        return degree_urls

    async def parse_page(self, ctx: PageContext) -> list[Degree | Course | Review]:
        soup: BeautifulSoup = ctx.html_soup
        program_name = self._extract_text_by_selectors(soup, PROGRAM_NAME_SELECTORS)
        degree_id = self._slugify(program_name) or self._url_to_slug(ctx.url)

        reviews: list[Review] = []
        for i, review_el in enumerate(soup.select(", ".join(REVIEW_SELECTORS))):
            raw_text = (
                self._extract_text_by_selectors(review_el, REVIEW_TEXT_SELECTORS)
                or review_el.get_text(strip=True)
            )
            if len(raw_text) < MIN_REVIEW_LENGTH:
                continue

            date_str = self._extract_text_by_selectors(review_el, REVIEW_DATE_SELECTORS, attr="datetime")
            ratings = self._extract_ratings(review_el)

            reviews.append(Review(
                degree_id=degree_id,
                source_slug=self.source_slug,
                source_url=ctx.url,
                source_id=self.generate_source_id(ctx.url, i, raw_text),
                raw_text=raw_text,
                language="he",
                posted_at=self._parse_date(date_str),
                author_handle=self._extract_text_by_selectors(review_el, REVIEW_AUTHOR_SELECTORS),
                metadata={"program_name": program_name, "ratings": ratings},
            ))

        return reviews

    @staticmethod
    def _extract_ratings(el: BeautifulSoup) -> dict:
        ratings = {}
        for rating_el in el.select("[data-rating]"):
            label = rating_el.get("data-label", "overall")
            try:
                ratings[label] = float(rating_el.get("data-rating", ""))
            except (ValueError, TypeError):
                pass
        return ratings
