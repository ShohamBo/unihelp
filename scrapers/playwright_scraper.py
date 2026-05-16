from bs4 import BeautifulSoup
from urllib.parse import urljoin

from .abstract_scraper import AbstractScraper
from .models import PageContext, Degree, Course, Review, ScraperResult
from .consts import BS4_HTML_PARSER
from .stealth import setup_stealth_page, jitter


class PlaywrightAbstractScraper(AbstractScraper):
    """
    AbstractScraper variant that uses Playwright instead of aiohttp.
    Use for sites with Cloudflare bot detection (403 to plain aiohttp).
    Subclasses implement the same get_subpages() / parse_page() interface.
    """

    async def _scrape(self) -> ScraperResult:
        from playwright.async_api import async_playwright

        result = ScraperResult(source_slug=self.source_slug)

        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=True)
            context = await browser.new_context(
                locale="he-IL",
                user_agent=(
                    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
                ),
            )
            page = await context.new_page()
            await setup_stealth_page(page)

            for dir_route in self.scraper_config.directories:
                dir_url = urljoin(self.scraper_config.base_url, dir_route)
                self.logger.info(f"[Playwright] Scraping directory {dir_url}")
                try:
                    await page.goto(dir_url, wait_until="domcontentloaded", timeout=30_000)
                    await jitter(1.0, 2.5)
                    html = await page.content()
                    soup = BeautifulSoup(html, BS4_HTML_PARSER)
                    subpage_urls = await self.get_subpages(soup, dir_url)
                    self.logger.info(f"Found {len(subpage_urls)} subpages")

                    for sub_url in subpage_urls:
                        try:
                            await page.goto(sub_url, wait_until="domcontentloaded", timeout=30_000)
                            await jitter(0.5, 1.5)
                            sub_html = await page.content()
                            sub_soup = BeautifulSoup(sub_html, BS4_HTML_PARSER)
                            ctx = PageContext(url=sub_url, html_soup=sub_soup)
                            items = await self.parse_page(ctx)
                            for item in items:
                                if isinstance(item, Degree):
                                    result.degrees.append(item)
                                elif isinstance(item, Course):
                                    result.courses.append(item)
                                elif isinstance(item, Review):
                                    result.reviews.append(item)
                        except Exception as e:
                            self.logger.warning(f"Failed subpage {sub_url}: {e}")

                except Exception as e:
                    self.logger.error(f"Failed directory {dir_url}: {e}", exc_info=True)

            await browser.close()
        return result
