from bs4 import BeautifulSoup

from ...playwright_scraper import PlaywrightAbstractScraper
from ...models import PageContext, Degree, Course, Review, ScraperResult
from .consts import (
    SOURCE_SLUG, INSTITUTION_SLUG,
    SCHOOL_URLS, PROGRAM_NAME_SELECTORS,
    SCHOOL_NAME_SELECTORS, DEGREE_LEVEL_SELECTORS,
    DUAL_MAJOR_KEYWORDS, EXTENDED_KEYWORD,
)


class ReichmanScraper(PlaywrightAbstractScraper):
    """
    Scrapes Reichman University (RUNI) programs via Playwright (JS SPA).
    Uses hardcoded school URLs since the site is a React app.
    """

    source_slug = SOURCE_SLUG

    async def get_subpages(self, soup: BeautifulSoup, directory_url: str) -> list[str]:
        return []

    async def parse_page(self, ctx: PageContext) -> list[Degree | Course | Review]:
        soup = ctx.html_soup
        name_he = self._extract_text_by_selectors(soup, PROGRAM_NAME_SELECTORS)
        if not name_he:
            return []

        slug = self._slugify(name_he) or self._url_to_slug(ctx.url)
        school_name = self._extract_text_by_selectors(soup, SCHOOL_NAME_SELECTORS)
        faculty_slug = self._slugify(school_name) if school_name else self._url_to_slug(ctx.url)
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

    async def _scrape(self) -> ScraperResult:
        from playwright.async_api import async_playwright
        from ...consts import BS4_HTML_PARSER
        from ...stealth import setup_stealth_page, jitter

        result = ScraperResult(source_slug=self.source_slug)
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=True)
            context = await browser.new_context(locale="he-IL")
            page = await context.new_page()
            await setup_stealth_page(page)

            for url in SCHOOL_URLS:
                try:
                    await page.goto(url, wait_until="networkidle", timeout=45_000)
                    await jitter(1.5, 3.0)
                    html = await page.content()
                    soup = BeautifulSoup(html, BS4_HTML_PARSER)
                    ctx = PageContext(url=url, html_soup=soup)
                    items = await self.parse_page(ctx)
                    for item in items:
                        if isinstance(item, Degree):
                            result.degrees.append(item)
                except Exception as e:
                    self.logger.warning(f"Failed school page {url}: {e}")

            await browser.close()
        return result
