import random
import asyncio

VIEWPORTS = [
    {"width": 1920, "height": 1080},
    {"width": 1366, "height": 768},
    {"width": 1440, "height": 900},
    {"width": 1280, "height": 800},
]

ACCEPT_LANGUAGES = [
    "he-IL,he;q=0.9,en-US;q=0.8,en;q=0.7",
    "he-IL,he;q=0.9",
    "en-US,en;q=0.9,he;q=0.8",
]


def random_viewport() -> dict:
    return random.choice(VIEWPORTS)


def random_accept_language() -> str:
    return random.choice(ACCEPT_LANGUAGES)


async def jitter(min_s: float = 0.5, max_s: float = 2.5):
    """Human-like inter-request delay."""
    await asyncio.sleep(random.uniform(min_s, max_s))


async def setup_stealth_page(page):
    """Apply stealth settings to a Playwright page object."""
    await page.set_viewport_size(random_viewport())
    await page.set_extra_http_headers({
        "Accept-Language": random_accept_language(),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
    })
    await page.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
        Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3]});
        Object.defineProperty(navigator, 'languages', {get: () => ['he-IL', 'he', 'en-US']});
    """)
