# Institutions Scrapers Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix three broken scrapers (wrong URLs / 403 Cloudflare), add a Playwright fallback abstract class for bot-protected sites, and build degree-scraping institution scrapers for all 10 Israeli universities and colleges under `scrapers/institutions/`.

**Architecture:** All institution scrapers extend `AbstractScraper` (two-method interface: `get_subpages`, `parse_page`). Cloudflare-protected sites (study, sce, reichman) use `PlaywrightAbstractScraper` which overrides `_scrape()` with headless Chromium + stealth headers from the existing `scrapers/stealth.py`. Every scraper has its own `config.yaml` and is invoked generically by the existing `run_scraper` Celery task.

**Tech Stack:** Python 3.10, aiohttp, Playwright (already in Docker image), BeautifulSoup4, Celery, YAML

> **Commit rule:** Do NOT commit after each task. One single commit at the very end (Task 15) covering all changes.

---

## Root Causes

| Scraper | Error | Root Cause | Fix |
|---------|-------|------------|-----|
| TauScraper | 404 | `tau.ac.il/he/faculties` does not exist | Move to `go.tau.ac.il`, use faculty area pages |
| TheStudentScraper | 404 | `/Degrees/` index doesn't exist; actual entry is `/Categories` | 2-hop discovery: `/Categories` → `/c[N]_*` → `/Degrees/Degree_N.html` |
| StudyScraper | 403 | Cloudflare TLS fingerprint detection | Replace aiohttp with Playwright + stealth |

## Verified URLs

| Institution | Base URL | Programs Catalog | Method |
|-------------|----------|-----------------|--------|
| TAU | `https://go.tau.ac.il` | Faculty areas: `/he/exact`, `/he/engineering`, `/he/humanities`, `/he/med`, `/he/life`, `/he/neuroscience`, `/he/education`, `/he/art`, `/he/social-sciences`, `/he/social-work`, `/he/management`, `/he/law` | aiohttp |
| HUJI | `https://info.huji.ac.il` | `/courses/first-degree/faculty/all/grid/all` → `/bachelor/{slug}` | aiohttp |
| Technion | `https://ugportal.technion.ac.il` | Faculty pages (hardcoded list) | aiohttp |
| BGU | `https://www.bgu.ac.il` | `/welcome/ba/catalog/` → `/welcome/ba/catalog/categories/{name}/` | aiohttp |
| BIU | `https://www.biu.ac.il` | `/catalog/%D7%AA%D7%95%D7%90%D7%A8%20%D7%A8%D7%90%D7%A9%D7%95%D7%9F` | aiohttp |
| Haifa | `https://admissions.haifa.ac.il` | `/bachelor/` → `/*/program/{N}/` | aiohttp |
| Reichman | `https://www.runi.ac.il` | JS SPA — Playwright required | Playwright |
| Afeka | `https://www.afeka.ac.il` | `/academic-departments/bsc/` | aiohttp |
| Ono | `https://www.ono.ac.il` | `/curriculum/` | aiohttp |
| SCE | `https://www.sce.ac.il` | `/academic-units1/` (403 on aiohttp) | Playwright |

## File Map

| File | Action |
|------|--------|
| `scrapers/thestudent/config.yaml` | directory `/Degrees/` → `/Categories` |
| `scrapers/thestudent/consts.py` | add category/degree link patterns |
| `scrapers/thestudent/scraper.py` | 2-hop `get_subpages()` |
| `scrapers/playwright_scraper.py` | new — `PlaywrightAbstractScraper` |
| `scrapers/study/scraper.py` | inherit `PlaywrightAbstractScraper` |
| `scrapers/institutions/__init__.py` | new — empty |
| `scrapers/institutions/tau/` | new — corrected TAU scraper |
| `scrapers/institutions/huji/` | new |
| `scrapers/institutions/technion/` | new |
| `scrapers/institutions/bgu/` | new |
| `scrapers/institutions/biu/` | new |
| `scrapers/institutions/haifa/` | new |
| `scrapers/institutions/reichman/` | new — Playwright |
| `scrapers/institutions/afeka/` | new |
| `scrapers/institutions/ono/` | new |
| `scrapers/institutions/sce/` | new — Playwright |
| `scrapers/tests/__init__.py` | new |
| `scrapers/tests/test_parsers.py` | new — unit tests for each parse_page() |

---

### Task 1: Fix TheStudent scraper (wrong URL)

**Files:**
- Modify: `scrapers/thestudent/config.yaml`
- Modify: `scrapers/thestudent/consts.py`
- Modify: `scrapers/thestudent/scraper.py`

**Background:** The scraper points at `/Degrees/` which returns 404. The correct entry point is `/Categories`, which lists category pages at `/c[N]_[name]`. Each category page links to individual degree pages at `/Degrees/Degree_[N].html`. `get_subpages()` must do two fetches: categories index → category pages → degree page URLs.

- [ ] **Step 1: Write failing test**

Create `scrapers/tests/__init__.py` (empty) and `scrapers/tests/test_parsers.py`:

```python
import pytest
from bs4 import BeautifulSoup
from unittest.mock import AsyncMock, patch, MagicMock


def make_thestudent_review_html() -> str:
    return """
    <html><body>
      <h1 class="degree-title">משפטים</h1>
      <div class="review-item">
        <p class="review-text">לימודים מאתגרים מאוד, ממליץ בחום.</p>
        <time datetime="2024-03-01">מרץ 2024</time>
        <span class="reviewer-name">דנה כהן</span>
      </div>
      <div class="review-item">
        <p class="review-text">קורסים מגוונים ומרצים מעולים, שווה.</p>
      </div>
    </body></html>
    """


@pytest.mark.asyncio
async def test_thestudent_parse_page_returns_reviews():
    from scrapers.thestudent.scraper import TheStudentScraper
    from scrapers.models import PageContext, Review

    soup = BeautifulSoup(make_thestudent_review_html(), "html.parser")
    ctx = PageContext(url="https://www.thestudent.co.il/Degrees/Degree_1.html", html_soup=soup)

    with patch.object(TheStudentScraper, "load_scraper_config") as mock_cfg:
        mock_cfg.return_value = MagicMock(
            base_url="https://www.thestudent.co.il",
            rate_limit=1.0, retries=1, proxy=None, directories=["/Categories"]
        )
        scraper = TheStudentScraper.__new__(TheStudentScraper)
        scraper.source_slug = "thestudent"
        from scrapers.common.logger_manager import scraper_logger
        scraper.logger = scraper_logger.get_child("thestudent")

        result = await scraper.parse_page(ctx)

    assert len(result) == 2
    assert all(isinstance(r, Review) for r in result)
    assert result[0].degree_id == "mshptym"
    assert result[0].posted_at is not None
    assert result[0].author_handle == "דנה כהן"
```

- [ ] **Step 2: Run test — expect failure**

```bash
cd C:\Users\user1\PycharmProjects\unihelp
python -m pytest scrapers/tests/test_parsers.py::test_thestudent_parse_page_returns_reviews -v
```

Expected: FAIL (import errors or assertion failure)

- [ ] **Step 3: Update `scrapers/thestudent/config.yaml`**

```yaml
base_url: "https://www.thestudent.co.il"
rate_limit: 0.5
directories:
  - "/Categories"
retries: 3
```

- [ ] **Step 4: Update `scrapers/thestudent/consts.py`**

```python
SOURCE_SLUG = "thestudent"
BASE_URL = "https://www.thestudent.co.il"
CATEGORIES_INDEX = "/Categories"

MIN_REVIEW_LENGTH = 30

REVIEW_SELECTORS = [".review-item", ".student-review", "article.review", "div[class*='review']"]
REVIEW_TEXT_SELECTORS = [".review-text", ".review-body", "p.content", "p"]
REVIEW_DATE_SELECTORS = ["time", ".review-date", "[class*='date']"]
REVIEW_AUTHOR_SELECTORS = [".reviewer-name", ".author-name", "[class*='author']"]
PROGRAM_NAME_SELECTORS = ["h1", ".degree-title", ".page-title"]
```

- [ ] **Step 5: Update `scrapers/thestudent/scraper.py`**

```python
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
```

- [ ] **Step 6: Run test — expect pass**

```bash
python -m pytest scrapers/tests/test_parsers.py::test_thestudent_parse_page_returns_reviews -v
```

Expected: PASS

---

### Task 2: Fix TAU scraper (wrong URL → go.tau.ac.il)

**Files:**
- Create: `scrapers/institutions/__init__.py`
- Create: `scrapers/institutions/tau/__init__.py`
- Create: `scrapers/institutions/tau/consts.py`
- Create: `scrapers/institutions/tau/config.yaml`
- Create: `scrapers/institutions/tau/scraper.py`

**Background:** `tau.ac.il/he/faculties` returns 404. The correct registration site is `go.tau.ac.il`. Faculty area pages (e.g. `/he/exact`, `/he/engineering`) each list programs with links at `/he/{area}/ba/{slug}` or `/he/{area}/ma/{slug}`. The scraper treats each faculty area as a directory and finds program links with `get_subpages()`.

- [ ] **Step 1: Write failing test**

Add to `scrapers/tests/test_parsers.py`:

```python
def make_tau_faculty_html() -> str:
    return """
    <html><body>
      <h1 class="page-title">מדעים מדויקים</h1>
      <div class="program-card">
        <a href="/he/exact/ba/statistics">סטטיסטיקה ומדע הנתונים</a>
      </div>
      <div class="program-card">
        <a href="/he/exact/ba/math">מתמטיקה</a>
      </div>
      <div class="program-card">
        <a href="/he/exact/ba/computer">מדעי המחשב</a>
      </div>
    </body></html>
    """


def make_tau_program_html() -> str:
    return """
    <html><body>
      <h1 class="page-title">סטטיסטיקה ומדע הנתונים</h1>
      <div class="degree-level">תואר ראשון</div>
      <div class="faculty-name">מדעים מדויקים</div>
      <p class="description">תכנית משולבת סטטיסטיקה ומדע נתונים.</p>
    </body></html>
    """


@pytest.mark.asyncio
async def test_tau_parse_page_returns_degree():
    from scrapers.institutions.tau.scraper import TauInstitutionScraper
    from scrapers.models import PageContext, Degree

    soup = BeautifulSoup(make_tau_program_html(), "html.parser")
    ctx = PageContext(
        url="https://go.tau.ac.il/he/exact/ba/statistics",
        html_soup=soup,
    )

    with patch.object(TauInstitutionScraper, "load_scraper_config") as mock_cfg:
        mock_cfg.return_value = MagicMock(
            base_url="https://go.tau.ac.il",
            rate_limit=1.0, retries=1, proxy=None,
            directories=["/he/exact"],
        )
        scraper = TauInstitutionScraper.__new__(TauInstitutionScraper)
        scraper.source_slug = "tau"
        from scrapers.common.logger_manager import scraper_logger
        scraper.logger = scraper_logger.get_child("tau")

        result = await scraper.parse_page(ctx)

    assert len(result) == 1
    deg = result[0]
    assert isinstance(deg, Degree)
    assert deg.institution_slug == "tau"
    assert deg.degree_level == "ba"
    assert "statist" in deg.slug or "sttystkh" in deg.slug
```

- [ ] **Step 2: Run test — expect failure**

```bash
python -m pytest scrapers/tests/test_parsers.py::test_tau_parse_page_returns_degree -v
```

Expected: FAIL (ModuleNotFoundError)

- [ ] **Step 3: Create directory structure**

```bash
mkdir -p scrapers/institutions/tau
touch scrapers/institutions/__init__.py
touch scrapers/institutions/tau/__init__.py
```

- [ ] **Step 4: Create `scrapers/institutions/tau/consts.py`**

```python
SOURCE_SLUG = "tau"
INSTITUTION_SLUG = "tau"
BASE_URL = "https://go.tau.ac.il"

# go.tau.ac.il URL pattern: /he/{faculty_area}/{degree_level}/{program_slug}
PROGRAM_LINK_RE = r"^/he/[^/]+/(ba|ma)/[^/]+"

PROGRAM_NAME_SELECTORS = ["h1", ".page-title", ".program-title", "h2"]
FACULTY_NAME_SELECTORS = [
    ".field--name-field-faculty", ".faculty-label",
    "[class*='faculty']", "nav .breadcrumb li:nth-child(2)",
]
DEGREE_LEVEL_SELECTORS = [
    ".degree-level", ".field--name-field-degree",
    "[class*='degree-level']", "[class*='degree-type']",
]
DUAL_MAJOR_KEYWORDS = ["דו-חוגי", "דו חוגי", "dual"]
EXTENDED_KEYWORD = "מורחב"

FACULTY_AREAS = [
    "/he/exact", "/he/engineering", "/he/humanities",
    "/he/med", "/he/life", "/he/neuroscience", "/he/education",
    "/he/art", "/he/social-sciences", "/he/social-work",
    "/he/management", "/he/law",
]
```

- [ ] **Step 5: Create `scrapers/institutions/tau/config.yaml`**

```yaml
base_url: "https://go.tau.ac.il"
rate_limit: 0.3
directories:
  - "/he/exact"
  - "/he/engineering"
  - "/he/humanities"
  - "/he/med"
  - "/he/life"
  - "/he/neuroscience"
  - "/he/education"
  - "/he/art"
  - "/he/social-sciences"
  - "/he/social-work"
  - "/he/management"
  - "/he/law"
retries: 3
```

- [ ] **Step 6: Create `scrapers/institutions/tau/scraper.py`**

```python
import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from ...abstract_scraper import AbstractScraper
from ...models import PageContext, Degree, Course, Review
from .consts import (
    SOURCE_SLUG, INSTITUTION_SLUG, BASE_URL, PROGRAM_LINK_RE,
    PROGRAM_NAME_SELECTORS, FACULTY_NAME_SELECTORS, DEGREE_LEVEL_SELECTORS,
    DUAL_MAJOR_KEYWORDS, EXTENDED_KEYWORD,
)

_PROGRAM_RE = re.compile(PROGRAM_LINK_RE)


class TauInstitutionScraper(AbstractScraper):
    """
    Scrapes TAU degree programs from go.tau.ac.il.
    Directory = one faculty area page (e.g. /he/exact).
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
            if _PROGRAM_RE.match(href):
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

        # Extract degree level and faculty from URL path: /he/{faculty}/{ba|ma}/{slug}
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
```

- [ ] **Step 7: Run test — expect pass**

```bash
python -m pytest scrapers/tests/test_parsers.py::test_tau_parse_page_returns_degree -v
```

Expected: PASS

---

### Task 3: Add `PlaywrightAbstractScraper`

**Files:**
- Create: `scrapers/playwright_scraper.py`

**Background:** study.co.il, sce.ac.il, and runi.ac.il all return 403 to aiohttp because Cloudflare checks the TLS fingerprint. Playwright uses a real Chromium binary, bypassing fingerprint detection. `stealth.py` already provides `setup_stealth_page()`. This new class overrides `_scrape()` only — subclasses still implement the same `get_subpages` / `parse_page` interface.

- [ ] **Step 1: Create `scrapers/playwright_scraper.py`**

```python
import asyncio

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
```

- [ ] **Step 2: Verify syntax**

```bash
python -m py_compile scrapers/playwright_scraper.py && echo OK
```

Expected: OK

---

### Task 4: Fix Study.co.il (403 → Playwright)

**Files:**
- Modify: `scrapers/study/scraper.py`
- Modify: `scrapers/study/consts.py`

**Background:** study.co.il returns 403 to aiohttp due to Cloudflare. Switch to `PlaywrightAbstractScraper`. The `get_subpages` and `parse_page` logic stays the same; only the HTTP layer changes.

- [ ] **Step 1: Update `scrapers/study/consts.py`**

```python
SOURCE_SLUG = "study"
BASE_URL = "https://www.study.co.il"

MIN_REVIEW_LENGTH = 30

INSTITUTION_NAME_MAP: dict[str, str] = {
    "אוניברסיטת תל אביב": "tau",
    "האוניברסיטה העברית": "huji",
    "הטכניון": "technion",
    "בן גוריון": "bgu",
    "אוניברסיטת בר-אילן": "biu",
    "אוניברסיטת חיפה": "haifa",
    "אוניברסיטת רייכמן": "reichman",
    "אפקה": "afeka",
    "אונו": "ono",
    "סמי שמעון": "sce",
}

# study.co.il program links: /P[N]/ or encoded Hebrew paths
PROGRAM_LINK_SELECTORS = [
    "a[href*='/P']", "a[href*='/degree/']",
    "a[href*='/program/']", ".program-card a", ".degree-link",
]
REVIEW_SELECTORS = [".review", ".student-review", ".feedback-item", "article.review", "[class*='review-']"]
REVIEW_TEXT_SELECTORS = [".review-content", ".review-text", ".review-body", "p.review", "p"]
REVIEW_DATE_SELECTORS = ["time", ".date", "[class*='date']", "[datetime]"]
PROGRAM_NAME_SELECTORS = ["h1", ".program-title", ".page-title", ".degree-title"]
INSTITUTION_NAME_SELECTORS = [
    ".institution-name", ".university-name",
    "[class*='university']", "[class*='college']", "[class*='institution']",
]
```

- [ ] **Step 2: Update `scrapers/study/scraper.py`**

```python
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from ..playwright_scraper import PlaywrightAbstractScraper
from ..models import PageContext, Degree, Course, Review
from .consts import (
    SOURCE_SLUG, BASE_URL, MIN_REVIEW_LENGTH, INSTITUTION_NAME_MAP,
    PROGRAM_LINK_SELECTORS, REVIEW_SELECTORS, REVIEW_TEXT_SELECTORS,
    REVIEW_DATE_SELECTORS, PROGRAM_NAME_SELECTORS, INSTITUTION_NAME_SELECTORS,
)


class StudyScraper(PlaywrightAbstractScraper):
    """
    Scrapes student reviews from study.co.il via Playwright (Cloudflare bypass).
    Directory (/) → program pages → Review objects per page.
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
        program_name = self._extract_text_by_selectors(soup, PROGRAM_NAME_SELECTORS)
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
```

- [ ] **Step 3: Verify syntax**

```bash
python -m py_compile scrapers/study/scraper.py && echo OK
```

Expected: OK

---

### Task 5: HUJI scraper

**Files:**
- Create: `scrapers/institutions/huji/__init__.py`
- Create: `scrapers/institutions/huji/consts.py`
- Create: `scrapers/institutions/huji/config.yaml`
- Create: `scrapers/institutions/huji/scraper.py`

**Background:** `info.huji.ac.il/courses/first-degree/faculty/all/grid/all` lists all bachelor's programs as cards with links `/bachelor/{slug}`. Each program page has `h1` for name, faculty info, and description. Confirmed static HTML — aiohttp works.

- [ ] **Step 1: Write test**

Add to `scrapers/tests/test_parsers.py`:

```python
def make_huji_program_html() -> str:
    return """
    <html><body>
      <h1 class="page-title">מדעי המחשב</h1>
      <div class="faculty-name">הפקולטה למדעים</div>
      <div class="degree-info">תואר ראשון - B.Sc</div>
      <p>תכנית לימודים במדעי המחשב.</p>
    </body></html>
    """


@pytest.mark.asyncio
async def test_huji_parse_page_returns_degree():
    from scrapers.institutions.huji.scraper import HujiScraper
    from scrapers.models import PageContext, Degree

    soup = BeautifulSoup(make_huji_program_html(), "html.parser")
    ctx = PageContext(url="https://info.huji.ac.il/bachelor/Computer-Sciences", html_soup=soup)

    with patch.object(HujiScraper, "load_scraper_config") as mock_cfg:
        mock_cfg.return_value = MagicMock(
            base_url="https://info.huji.ac.il",
            rate_limit=1.0, retries=1, proxy=None,
            directories=["/courses/first-degree/faculty/all/grid/all"],
        )
        scraper = HujiScraper.__new__(HujiScraper)
        scraper.source_slug = "huji"
        from scrapers.common.logger_manager import scraper_logger
        scraper.logger = scraper_logger.get_child("huji")

        result = await scraper.parse_page(ctx)

    assert len(result) == 1
    deg = result[0]
    assert isinstance(deg, Degree)
    assert deg.institution_slug == "huji"
    assert deg.degree_level == "ba"
```

- [ ] **Step 2: Run test — expect failure**

```bash
python -m pytest scrapers/tests/test_parsers.py::test_huji_parse_page_returns_degree -v
```

- [ ] **Step 3: Create `scrapers/institutions/huji/__init__.py`** (empty)

- [ ] **Step 4: Create `scrapers/institutions/huji/consts.py`**

```python
SOURCE_SLUG = "huji"
INSTITUTION_SLUG = "huji"
BASE_URL = "https://info.huji.ac.il"

PROGRAM_LINK_SELECTORS = [
    "a[href^='/bachelor/']", "a[href*='/bachelor/']",
    ".program-card a", ".degree-card a",
]
PROGRAM_NAME_SELECTORS = ["h1", ".page-title", ".program-title"]
FACULTY_NAME_SELECTORS = [
    ".faculty-name", ".field--name-field-faculty",
    "[class*='faculty']", ".breadcrumb li:nth-child(2)",
]
DEGREE_LEVEL_SELECTORS = [
    ".degree-info", ".degree-level", "[class*='degree-level']",
    ".field--name-field-degree-level",
]
DUAL_MAJOR_KEYWORDS = ["דו-חוגי", "דו חוגי", "combined", "joint"]
EXTENDED_KEYWORD = "מורחב"
```

- [ ] **Step 5: Create `scrapers/institutions/huji/config.yaml`**

```yaml
base_url: "https://info.huji.ac.il"
rate_limit: 0.4
directories:
  - "/courses/first-degree/faculty/all/grid/all"
retries: 3
```

- [ ] **Step 6: Create `scrapers/institutions/huji/scraper.py`**

```python
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


class HujiScraper(AbstractScraper):
    """
    Scrapes HUJI bachelor's programs from info.huji.ac.il.
    Directory: /courses/first-degree/faculty/all/grid/all
    Sub-pages: /bachelor/{slug}
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
        soup = ctx.html_soup
        name_he = self._extract_text_by_selectors(soup, PROGRAM_NAME_SELECTORS)
        if not name_he:
            return []

        slug = self._slugify(name_he)
        if not slug:
            slug = ctx.url.rstrip("/").split("/")[-1]

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
```

- [ ] **Step 7: Run test — expect pass**

```bash
python -m pytest scrapers/tests/test_parsers.py::test_huji_parse_page_returns_degree -v
```

---

### Task 6: Technion scraper

**Files:**
- Create: `scrapers/institutions/technion/__init__.py`
- Create: `scrapers/institutions/technion/consts.py`
- Create: `scrapers/institutions/technion/config.yaml`
- Create: `scrapers/institutions/technion/scraper.py`

**Background:** Technion's central ugportal has no scrapeable program list (SAP-based). Each faculty has its own subdomain (`cs.technion.ac.il`, `ece.technion.ac.il`, etc.) with its own undergraduate page. We use a hardcoded directory list covering all known faculties. `get_subpages()` finds "undergraduate" links on each faculty homepage, and `parse_page()` extracts the program name + degree level.

- [ ] **Step 1: Write test**

```python
def make_technion_program_html() -> str:
    return """
    <html><body>
      <h1>הפקולטה למדעי המחשב</h1>
      <div class="program-info">
        <h2>תואר ראשון במדעי המחשב</h2>
        <p>תכנית לימודים רב-שנתית.</p>
      </div>
    </body></html>
    """


@pytest.mark.asyncio
async def test_technion_parse_page_returns_degree():
    from scrapers.institutions.technion.scraper import TechnionScraper
    from scrapers.models import PageContext, Degree

    soup = BeautifulSoup(make_technion_program_html(), "html.parser")
    ctx = PageContext(url="https://cs.technion.ac.il/he/undergraduate/", html_soup=soup)

    with patch.object(TechnionScraper, "load_scraper_config") as mock_cfg:
        mock_cfg.return_value = MagicMock(
            base_url="https://ugportal.technion.ac.il",
            rate_limit=1.0, retries=1, proxy=None,
            directories=[],
        )
        scraper = TechnionScraper.__new__(TechnionScraper)
        scraper.source_slug = "technion"
        from scrapers.common.logger_manager import scraper_logger
        scraper.logger = scraper_logger.get_child("technion")

        result = await scraper.parse_page(ctx)

    assert len(result) >= 1
    deg = result[0]
    assert isinstance(deg, Degree)
    assert deg.institution_slug == "technion"
    assert deg.degree_level == "ba"
```

- [ ] **Step 2: Run test — expect failure**

```bash
python -m pytest scrapers/tests/test_parsers.py::test_technion_parse_page_returns_degree -v
```

- [ ] **Step 3: Create `scrapers/institutions/technion/__init__.py`** (empty)

- [ ] **Step 4: Create `scrapers/institutions/technion/consts.py`**

```python
SOURCE_SLUG = "technion"
INSTITUTION_SLUG = "technion"
BASE_URL = "https://ugportal.technion.ac.il"

# Known faculty undergraduate pages (confirmed live)
FACULTY_UNDERGRADUATE_URLS = [
    "https://cs.technion.ac.il/he/undergraduate/",
    "https://ece.technion.ac.il/",
    "https://meeng.technion.ac.il/",
    "https://cee.technion.ac.il/en/division/undergraduate-programs/",
    "https://chemistry.technion.ac.il/undergraduate/",
    "https://physics.technion.ac.il/undergraduate/",
    "https://math.technion.ac.il/undergraduate/",
    "https://ie.technion.ac.il/undergraduate/",
    "https://bio.technion.ac.il/undergraduate/",
    "https://arch.technion.ac.il/undergraduate/",
]

PROGRAM_NAME_SELECTORS = ["h1", "h2.program-title", ".page-title", "h2"]
FACULTY_NAME_SELECTORS = ["h1", ".faculty-title", ".page-title"]
DEGREE_LEVEL_SELECTORS = [".degree-level", "[class*='degree']", "h2", "h3"]
UNDERGRADUATE_LINK_KEYWORDS = ["undergraduate", "תואר-ראשון", "bachelor", "bsc", "b.sc"]
DUAL_MAJOR_KEYWORDS = ["דו-חוגי", "combined", "joint"]
EXTENDED_KEYWORD = "מורחב"
```

- [ ] **Step 5: Create `scrapers/institutions/technion/config.yaml`**

```yaml
base_url: "https://ugportal.technion.ac.il"
rate_limit: 0.4
directories: []
retries: 3
```

- [ ] **Step 6: Create `scrapers/institutions/technion/scraper.py`**

```python
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
```

- [ ] **Step 7: Run test — expect pass**

```bash
python -m pytest scrapers/tests/test_parsers.py::test_technion_parse_page_returns_degree -v
```

---

### Task 7: BGU scraper

**Files:**
- Create: `scrapers/institutions/bgu/__init__.py`
- Create: `scrapers/institutions/bgu/consts.py`
- Create: `scrapers/institutions/bgu/config.yaml`
- Create: `scrapers/institutions/bgu/scraper.py`

**Background:** `bgu.ac.il/welcome/ba/catalog/` lists all BA programs with links to category pages at `/welcome/ba/catalog/categories/{name}/`. Each category page lists programs. The site is standard static HTML.

- [ ] **Step 1: Write test**

```python
def make_bgu_catalog_html() -> str:
    return """
    <html><body>
      <h1>קטלוג תוכניות</h1>
      <a href="/welcome/ba/catalog/categories/computer-science/">מדעי המחשב</a>
      <a href="/welcome/ba/catalog/categories/mathematics/">מתמטיקה</a>
      <a href="/welcome/ba/catalog/categories/psychology/">פסיכולוגיה</a>
    </body></html>
    """


def make_bgu_program_html() -> str:
    return """
    <html><body>
      <h1 class="program-title">מדעי המחשב</h1>
      <div class="faculty">הפקולטה למדעי המחשב</div>
      <div class="degree-type">תואר ראשון B.Sc</div>
    </body></html>
    """


@pytest.mark.asyncio
async def test_bgu_parse_page_returns_degree():
    from scrapers.institutions.bgu.scraper import BguScraper
    from scrapers.models import PageContext, Degree

    soup = BeautifulSoup(make_bgu_program_html(), "html.parser")
    ctx = PageContext(
        url="https://www.bgu.ac.il/welcome/ba/catalog/categories/computer-science/",
        html_soup=soup,
    )

    with patch.object(BguScraper, "load_scraper_config") as mock_cfg:
        mock_cfg.return_value = MagicMock(
            base_url="https://www.bgu.ac.il", rate_limit=1.0,
            retries=1, proxy=None, directories=["/welcome/ba/catalog/"],
        )
        scraper = BguScraper.__new__(BguScraper)
        scraper.source_slug = "bgu"
        from scrapers.common.logger_manager import scraper_logger
        scraper.logger = scraper_logger.get_child("bgu")
        result = await scraper.parse_page(ctx)

    assert len(result) == 1
    deg = result[0]
    assert isinstance(deg, Degree)
    assert deg.institution_slug == "bgu"
    assert deg.degree_level == "ba"
```

- [ ] **Step 2: Run test — expect failure**

```bash
python -m pytest scrapers/tests/test_parsers.py::test_bgu_parse_page_returns_degree -v
```

- [ ] **Step 3: Create `scrapers/institutions/bgu/__init__.py`** (empty)

- [ ] **Step 4: Create `scrapers/institutions/bgu/consts.py`**

```python
SOURCE_SLUG = "bgu"
INSTITUTION_SLUG = "bgu"
BASE_URL = "https://www.bgu.ac.il"

CATEGORY_LINK_SELECTORS = [
    "a[href*='/catalog/categories/']",
    "a[href*='/welcome/ba/catalog/']",
    ".catalog-item a", ".program-category a",
]
PROGRAM_NAME_SELECTORS = ["h1", ".program-title", ".page-title", "h2.title"]
FACULTY_NAME_SELECTORS = [
    ".faculty", ".faculty-name", "[class*='faculty']",
    ".breadcrumb li:nth-child(2)",
]
DEGREE_LEVEL_SELECTORS = [".degree-type", ".degree-level", "[class*='degree']"]
DUAL_MAJOR_KEYWORDS = ["דו-חוגי", "דו מחלקתי", "combined"]
EXTENDED_KEYWORD = "מורחב"
```

- [ ] **Step 5: Create `scrapers/institutions/bgu/config.yaml`**

```yaml
base_url: "https://www.bgu.ac.il"
rate_limit: 0.4
directories:
  - "/welcome/ba/catalog/"
retries: 3
```

- [ ] **Step 6: Create `scrapers/institutions/bgu/scraper.py`**

```python
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from ...abstract_scraper import AbstractScraper
from ...models import PageContext, Degree, Course, Review
from .consts import (
    SOURCE_SLUG, INSTITUTION_SLUG, BASE_URL,
    CATEGORY_LINK_SELECTORS, PROGRAM_NAME_SELECTORS,
    FACULTY_NAME_SELECTORS, DEGREE_LEVEL_SELECTORS,
    DUAL_MAJOR_KEYWORDS, EXTENDED_KEYWORD,
)


class BguScraper(AbstractScraper):
    """
    Scrapes BGU BA programs from bgu.ac.il/welcome/ba/catalog/.
    get_subpages() finds category links; parse_page() extracts Degree from each category page.
    """

    source_slug = SOURCE_SLUG

    async def get_subpages(self, soup: BeautifulSoup, directory_url: str) -> list[str]:
        seen: set[str] = set()
        urls: list[str] = []
        for selector in CATEGORY_LINK_SELECTORS:
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
```

- [ ] **Step 7: Run test — expect pass**

```bash
python -m pytest scrapers/tests/test_parsers.py::test_bgu_parse_page_returns_degree -v
```

---

### Task 8: BIU scraper

**Files:**
- Create: `scrapers/institutions/biu/__init__.py`
- Create: `scrapers/institutions/biu/consts.py`
- Create: `scrapers/institutions/biu/config.yaml`
- Create: `scrapers/institutions/biu/scraper.py`

- [ ] **Step 1: Write test**

```python
def make_biu_program_html() -> str:
    return """
    <html><body>
      <h1 class="page-title">פסיכולוגיה</h1>
      <div class="faculty-title">הפקולטה למדעי החברה</div>
      <div class="degree-level">תואר ראשון</div>
    </body></html>
    """


@pytest.mark.asyncio
async def test_biu_parse_page_returns_degree():
    from scrapers.institutions.biu.scraper import BiuScraper
    from scrapers.models import PageContext, Degree

    soup = BeautifulSoup(make_biu_program_html(), "html.parser")
    ctx = PageContext(url="https://www.biu.ac.il/catalog/psychology", html_soup=soup)

    with patch.object(BiuScraper, "load_scraper_config") as mock_cfg:
        mock_cfg.return_value = MagicMock(
            base_url="https://www.biu.ac.il", rate_limit=1.0,
            retries=1, proxy=None,
            directories=["/catalog/%D7%AA%D7%95%D7%90%D7%A8%20%D7%A8%D7%90%D7%A9%D7%95%D7%9F"],
        )
        scraper = BiuScraper.__new__(BiuScraper)
        scraper.source_slug = "biu"
        from scrapers.common.logger_manager import scraper_logger
        scraper.logger = scraper_logger.get_child("biu")
        result = await scraper.parse_page(ctx)

    assert len(result) == 1
    assert result[0].institution_slug == "biu"
    assert result[0].degree_level == "ba"
```

- [ ] **Step 2: Run — expect failure**

```bash
python -m pytest scrapers/tests/test_parsers.py::test_biu_parse_page_returns_degree -v
```

- [ ] **Step 3: Create `scrapers/institutions/biu/__init__.py`** (empty)

- [ ] **Step 4: Create `scrapers/institutions/biu/consts.py`**

```python
SOURCE_SLUG = "biu"
INSTITUTION_SLUG = "biu"
BASE_URL = "https://www.biu.ac.il"

PROGRAM_LINK_SELECTORS = [
    "a[href*='/catalog/']", ".program-item a",
    ".degree-card a", "[class*='catalog'] a",
]
PROGRAM_NAME_SELECTORS = ["h1", ".page-title", ".program-title", "h2.title"]
FACULTY_NAME_SELECTORS = [
    ".faculty-title", ".faculty-name", "[class*='faculty']",
    ".breadcrumb li:nth-child(2)",
]
DEGREE_LEVEL_SELECTORS = [".degree-level", ".degree-type", "[class*='degree']"]
DUAL_MAJOR_KEYWORDS = ["דו-חוגי", "combined", "joint"]
EXTENDED_KEYWORD = "מורחב"
```

- [ ] **Step 5: Create `scrapers/institutions/biu/config.yaml`**

```yaml
base_url: "https://www.biu.ac.il"
rate_limit: 0.4
directories:
  - "/catalog/%D7%AA%D7%95%D7%90%D7%A8%20%D7%A8%D7%90%D7%A9%D7%95%D7%9F"
retries: 3
```

- [ ] **Step 6: Create `scrapers/institutions/biu/scraper.py`**

```python
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
```

- [ ] **Step 7: Run — expect pass**

```bash
python -m pytest scrapers/tests/test_parsers.py::test_biu_parse_page_returns_degree -v
```

---

### Task 9: Haifa scraper

**Files:**
- Create: `scrapers/institutions/haifa/__init__.py`
- Create: `scrapers/institutions/haifa/consts.py`
- Create: `scrapers/institutions/haifa/config.yaml`
- Create: `scrapers/institutions/haifa/scraper.py`

**Background:** `admissions.haifa.ac.il/bachelor/` lists all programs. Individual program pages follow the pattern `admissions.haifa.ac.il/{faculty}/program/{N}/`. Confirmed 60+ programs, static HTML.

- [ ] **Step 1: Write test**

```python
def make_haifa_program_html() -> str:
    return """
    <html><body>
      <h1 class="page-title">מדעי המחשב</h1>
      <div class="faculty-label">הפקולטה למדעי המחשב ומערכות מידע</div>
      <div class="degree-badge">תואר ראשון B.Sc</div>
    </body></html>
    """


@pytest.mark.asyncio
async def test_haifa_parse_page_returns_degree():
    from scrapers.institutions.haifa.scraper import HaifaScraper
    from scrapers.models import PageContext, Degree

    soup = BeautifulSoup(make_haifa_program_html(), "html.parser")
    ctx = PageContext(url="https://admissions.haifa.ac.il/computer-science/program/3210/", html_soup=soup)

    with patch.object(HaifaScraper, "load_scraper_config") as mock_cfg:
        mock_cfg.return_value = MagicMock(
            base_url="https://admissions.haifa.ac.il", rate_limit=1.0,
            retries=1, proxy=None, directories=["/bachelor/"],
        )
        scraper = HaifaScraper.__new__(HaifaScraper)
        scraper.source_slug = "haifa"
        from scrapers.common.logger_manager import scraper_logger
        scraper.logger = scraper_logger.get_child("haifa")
        result = await scraper.parse_page(ctx)

    assert len(result) == 1
    assert result[0].institution_slug == "haifa"
    assert result[0].degree_level == "ba"
```

- [ ] **Step 2: Run — expect failure**

```bash
python -m pytest scrapers/tests/test_parsers.py::test_haifa_parse_page_returns_degree -v
```

- [ ] **Step 3: Create `scrapers/institutions/haifa/__init__.py`** (empty)

- [ ] **Step 4: Create `scrapers/institutions/haifa/consts.py`**

```python
SOURCE_SLUG = "haifa"
INSTITUTION_SLUG = "haifa"
BASE_URL = "https://admissions.haifa.ac.il"

PROGRAM_LINK_SELECTORS = [
    "a[href*='/program/']", ".program-card a",
    ".degree-card a", "a[href*='/bachelor/']",
]
PROGRAM_NAME_SELECTORS = ["h1", ".page-title", ".program-title", "h2"]
FACULTY_NAME_SELECTORS = [
    ".faculty-label", ".faculty-name", "[class*='faculty']",
    ".breadcrumb li:nth-child(2)",
]
DEGREE_LEVEL_SELECTORS = [".degree-badge", ".degree-level", "[class*='degree']"]
DUAL_MAJOR_KEYWORDS = ["דו-חוגי", "רב-תחומי", "combined"]
EXTENDED_KEYWORD = "מורחב"
```

- [ ] **Step 5: Create `scrapers/institutions/haifa/config.yaml`**

```yaml
base_url: "https://admissions.haifa.ac.il"
rate_limit: 0.4
directories:
  - "/bachelor/"
retries: 3
```

- [ ] **Step 6: Create `scrapers/institutions/haifa/scraper.py`**

```python
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


class HaifaScraper(AbstractScraper):
    """Scrapes University of Haifa programs from admissions.haifa.ac.il/bachelor/."""

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
```

- [ ] **Step 7: Run — expect pass**

```bash
python -m pytest scrapers/tests/test_parsers.py::test_haifa_parse_page_returns_degree -v
```

---

### Task 10: Afeka scraper

**Files:**
- Create: `scrapers/institutions/afeka/__init__.py`
- Create: `scrapers/institutions/afeka/consts.py`
- Create: `scrapers/institutions/afeka/config.yaml`
- Create: `scrapers/institutions/afeka/scraper.py`

**Background:** `afeka.ac.il/academic-departments/bsc/` lists 11 BSc programs (single + double major). Each at `/academic-departments/bsc/{name}/`. Static HTML, no bot protection.

- [ ] **Step 1: Write test**

```python
def make_afeka_program_html() -> str:
    return """
    <html><body>
      <h1 class="page-title">הנדסת תוכנה</h1>
      <div class="degree-info">תואר ראשון B.Sc בהנדסת תוכנה</div>
    </body></html>
    """


@pytest.mark.asyncio
async def test_afeka_parse_page_returns_degree():
    from scrapers.institutions.afeka.scraper import AfekaScraper
    from scrapers.models import PageContext, Degree

    soup = BeautifulSoup(make_afeka_program_html(), "html.parser")
    ctx = PageContext(url="https://www.afeka.ac.il/academic-departments/bsc/software-engineering/", html_soup=soup)

    with patch.object(AfekaScraper, "load_scraper_config") as mock_cfg:
        mock_cfg.return_value = MagicMock(
            base_url="https://www.afeka.ac.il", rate_limit=1.0,
            retries=1, proxy=None, directories=["/academic-departments/bsc/"],
        )
        scraper = AfekaScraper.__new__(AfekaScraper)
        scraper.source_slug = "afeka"
        from scrapers.common.logger_manager import scraper_logger
        scraper.logger = scraper_logger.get_child("afeka")
        result = await scraper.parse_page(ctx)

    assert len(result) == 1
    assert result[0].institution_slug == "afeka"
    assert result[0].degree_level == "ba"
```

- [ ] **Step 2: Run — expect failure**

```bash
python -m pytest scrapers/tests/test_parsers.py::test_afeka_parse_page_returns_degree -v
```

- [ ] **Step 3: Create `scrapers/institutions/afeka/__init__.py`** (empty)

- [ ] **Step 4: Create `scrapers/institutions/afeka/consts.py`**

```python
SOURCE_SLUG = "afeka"
INSTITUTION_SLUG = "afeka"
BASE_URL = "https://www.afeka.ac.il"

PROGRAM_LINK_SELECTORS = [
    "a[href*='/bsc/']", ".program-card a",
    ".department-card a", "[class*='program'] a",
]
PROGRAM_NAME_SELECTORS = ["h1", ".page-title", ".program-title"]
DEGREE_LEVEL_SELECTORS = [".degree-info", ".degree-level", "[class*='degree']"]
DUAL_MAJOR_KEYWORDS = ["ומדעי המחשב", "combined", "dual"]
EXTENDED_KEYWORD = "מורחב"
```

- [ ] **Step 5: Create `scrapers/institutions/afeka/config.yaml`**

```yaml
base_url: "https://www.afeka.ac.il"
rate_limit: 0.5
directories:
  - "/academic-departments/bsc/"
retries: 3
```

- [ ] **Step 6: Create `scrapers/institutions/afeka/scraper.py`**

```python
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from ...abstract_scraper import AbstractScraper
from ...models import PageContext, Degree, Course, Review
from .consts import (
    SOURCE_SLUG, INSTITUTION_SLUG, BASE_URL,
    PROGRAM_LINK_SELECTORS, PROGRAM_NAME_SELECTORS,
    DEGREE_LEVEL_SELECTORS, DUAL_MAJOR_KEYWORDS, EXTENDED_KEYWORD,
)


class AfekaScraper(AbstractScraper):
    """Scrapes Afeka engineering BSc programs from afeka.ac.il/academic-departments/bsc/."""

    source_slug = SOURCE_SLUG

    async def get_subpages(self, soup: BeautifulSoup, directory_url: str) -> list[str]:
        seen: set[str] = set()
        urls: list[str] = []
        for selector in PROGRAM_LINK_SELECTORS:
            for link in soup.select(selector):
                href = link.get("href", "")
                if not href or href.rstrip("/") == "/academic-departments/bsc":
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
        degree_raw = self._extract_text_by_selectors(soup, DEGREE_LEVEL_SELECTORS)

        return [Degree(
            institution_slug=INSTITUTION_SLUG,
            slug=slug,
            name_he=name_he,
            faculty_slug="engineering",
            degree_level=self._normalize_degree(degree_raw or "ba"),
            is_dual_major=any(kw in name_he for kw in DUAL_MAJOR_KEYWORDS),
            is_extended=EXTENDED_KEYWORD in name_he,
            canonical_url=ctx.url,
            metadata={},
            source_slug=self.source_slug,
        )]
```

- [ ] **Step 7: Run — expect pass**

```bash
python -m pytest scrapers/tests/test_parsers.py::test_afeka_parse_page_returns_degree -v
```

---

### Task 11: Ono scraper

**Files:**
- Create: `scrapers/institutions/ono/__init__.py`
- Create: `scrapers/institutions/ono/consts.py`
- Create: `scrapers/institutions/ono/config.yaml`
- Create: `scrapers/institutions/ono/scraper.py`

**Background:** `ono.ac.il/curriculum/` lists all programs. Individual programs at `/curriculum/{slug}/`. Confirmed static HTML with multiple faculties.

- [ ] **Step 1: Write test**

```python
def make_ono_program_html() -> str:
    return """
    <html><body>
      <h1 class="entry-title">משפטים - תואר ראשון LL.B</h1>
      <div class="faculty-name">הפקולטה למשפטים</div>
    </body></html>
    """


@pytest.mark.asyncio
async def test_ono_parse_page_returns_degree():
    from scrapers.institutions.ono.scraper import OnoScraper
    from scrapers.models import PageContext, Degree

    soup = BeautifulSoup(make_ono_program_html(), "html.parser")
    ctx = PageContext(url="https://www.ono.ac.il/curriculum/llb/", html_soup=soup)

    with patch.object(OnoScraper, "load_scraper_config") as mock_cfg:
        mock_cfg.return_value = MagicMock(
            base_url="https://www.ono.ac.il", rate_limit=1.0,
            retries=1, proxy=None, directories=["/curriculum/"],
        )
        scraper = OnoScraper.__new__(OnoScraper)
        scraper.source_slug = "ono"
        from scrapers.common.logger_manager import scraper_logger
        scraper.logger = scraper_logger.get_child("ono")
        result = await scraper.parse_page(ctx)

    assert len(result) == 1
    assert result[0].institution_slug == "ono"
```

- [ ] **Step 2: Run — expect failure**

```bash
python -m pytest scrapers/tests/test_parsers.py::test_ono_parse_page_returns_degree -v
```

- [ ] **Step 3: Create `scrapers/institutions/ono/__init__.py`** (empty)

- [ ] **Step 4: Create `scrapers/institutions/ono/consts.py`**

```python
SOURCE_SLUG = "ono"
INSTITUTION_SLUG = "ono"
BASE_URL = "https://www.ono.ac.il"

PROGRAM_LINK_SELECTORS = [
    "a[href*='/curriculum/']", ".program-card a",
    ".curriculum-item a", "nav a[href*='/curriculum/']",
]
PROGRAM_NAME_SELECTORS = ["h1", ".entry-title", ".page-title", ".program-title"]
FACULTY_NAME_SELECTORS = [".faculty-name", "[class*='faculty']", ".breadcrumb li:nth-child(2)"]
DEGREE_LEVEL_SELECTORS = [".degree-type", ".degree-level", "[class*='degree']", "h1"]
DUAL_MAJOR_KEYWORDS = ["דו-חוגי", "combined"]
EXTENDED_KEYWORD = "מורחב"
```

- [ ] **Step 5: Create `scrapers/institutions/ono/config.yaml`**

```yaml
base_url: "https://www.ono.ac.il"
rate_limit: 0.5
directories:
  - "/curriculum/"
retries: 3
```

- [ ] **Step 6: Create `scrapers/institutions/ono/scraper.py`**

```python
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


class OnoScraper(AbstractScraper):
    """Scrapes Ono Academic College programs from ono.ac.il/curriculum/."""

    source_slug = SOURCE_SLUG

    async def get_subpages(self, soup: BeautifulSoup, directory_url: str) -> list[str]:
        seen: set[str] = set()
        urls: list[str] = []
        for selector in PROGRAM_LINK_SELECTORS:
            for link in soup.select(selector):
                href = link.get("href", "")
                if not href or href.rstrip("/") in ("/curriculum", ""):
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
```

- [ ] **Step 7: Run — expect pass**

```bash
python -m pytest scrapers/tests/test_parsers.py::test_ono_parse_page_returns_degree -v
```

---

### Task 12: Reichman scraper (Playwright — JS SPA)

**Files:**
- Create: `scrapers/institutions/reichman/__init__.py`
- Create: `scrapers/institutions/reichman/consts.py`
- Create: `scrapers/institutions/reichman/config.yaml`
- Create: `scrapers/institutions/reichman/scraper.py`

**Background:** `runi.ac.il` is a React SPA — fetching with aiohttp returns empty HTML. Playwright renders the JS and provides actual content. Programs are organized by school (Business, Government, Psychology, Computer Science, Communications, Law, Sustainability).

- [ ] **Step 1: Write test**

```python
def make_reichman_program_html() -> str:
    return """
    <html><body>
      <h1 class="school-title">מדעי המחשב</h1>
      <div class="degree-type">תואר ראשון B.Sc</div>
      <div class="school-name">בית הספר למדעי המחשב</div>
    </body></html>
    """


@pytest.mark.asyncio
async def test_reichman_parse_page_returns_degree():
    from scrapers.institutions.reichman.scraper import ReichmanScraper
    from scrapers.models import PageContext, Degree

    soup = BeautifulSoup(make_reichman_program_html(), "html.parser")
    ctx = PageContext(url="https://www.runi.ac.il/he/schools/cs/", html_soup=soup)

    with patch.object(ReichmanScraper, "load_scraper_config") as mock_cfg:
        mock_cfg.return_value = MagicMock(
            base_url="https://www.runi.ac.il", rate_limit=1.0,
            retries=1, proxy=None, directories=["/he/schools/"],
        )
        scraper = ReichmanScraper.__new__(ReichmanScraper)
        scraper.source_slug = "reichman"
        from scrapers.common.logger_manager import scraper_logger
        scraper.logger = scraper_logger.get_child("reichman")
        result = await scraper.parse_page(ctx)

    assert len(result) == 1
    assert result[0].institution_slug == "reichman"
    assert result[0].degree_level == "ba"
```

- [ ] **Step 2: Run — expect failure**

```bash
python -m pytest scrapers/tests/test_parsers.py::test_reichman_parse_page_returns_degree -v
```

- [ ] **Step 3: Create `scrapers/institutions/reichman/__init__.py`** (empty)

- [ ] **Step 4: Create `scrapers/institutions/reichman/consts.py`**

```python
SOURCE_SLUG = "reichman"
INSTITUTION_SLUG = "reichman"
BASE_URL = "https://www.runi.ac.il"

# Hardcoded school pages (JS SPA — no crawlable directory)
SCHOOL_URLS = [
    "https://www.runi.ac.il/he/schools/business/",
    "https://www.runi.ac.il/he/schools/government/",
    "https://www.runi.ac.il/he/schools/psychology/",
    "https://www.runi.ac.il/he/schools/cs/",
    "https://www.runi.ac.il/he/schools/communications/",
    "https://www.runi.ac.il/he/schools/law/",
    "https://www.runi.ac.il/he/schools/sustainability/",
    "https://www.runi.ac.il/he/schools/design/",
]

PROGRAM_NAME_SELECTORS = ["h1", ".school-title", ".page-title", ".program-title"]
SCHOOL_NAME_SELECTORS = [".school-name", ".faculty-name", "[class*='school']", "h2"]
DEGREE_LEVEL_SELECTORS = [".degree-type", ".degree-level", "[class*='degree']"]
DUAL_MAJOR_KEYWORDS = ["דו-חוגי", "combined"]
EXTENDED_KEYWORD = "מורחב"
```

- [ ] **Step 5: Create `scrapers/institutions/reichman/config.yaml`**

```yaml
base_url: "https://www.runi.ac.il"
rate_limit: 1.0
directories:
  - "/he/schools/"
retries: 3
```

- [ ] **Step 6: Create `scrapers/institutions/reichman/scraper.py`**

```python
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
        from urllib.parse import urljoin

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
                    from bs4 import BeautifulSoup
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
```

- [ ] **Step 7: Run — expect pass**

```bash
python -m pytest scrapers/tests/test_parsers.py::test_reichman_parse_page_returns_degree -v
```

---

### Task 13: SCE scraper (Playwright — 403 on aiohttp)

**Files:**
- Create: `scrapers/institutions/sce/__init__.py`
- Create: `scrapers/institutions/sce/consts.py`
- Create: `scrapers/institutions/sce/config.yaml`
- Create: `scrapers/institutions/sce/scraper.py`

**Background:** `sce.ac.il` returns 403 to aiohttp. Playwright bypasses this. Programs are at `/academic-units1/{campus}/{faculty}/{program}`. Two campuses: beersheva, ashdod.

- [ ] **Step 1: Write test**

```python
def make_sce_program_html() -> str:
    return """
    <html><body>
      <h1 class="page-title">הנדסת תוכנה</h1>
      <div class="department-faculty">הנדסה</div>
      <div class="degree-level">תואר ראשון B.Sc</div>
    </body></html>
    """


@pytest.mark.asyncio
async def test_sce_parse_page_returns_degree():
    from scrapers.institutions.sce.scraper import SceScraper
    from scrapers.models import PageContext, Degree

    soup = BeautifulSoup(make_sce_program_html(), "html.parser")
    ctx = PageContext(
        url="https://www.sce.ac.il/academic-units1/ashdod/engineering/software-engineering",
        html_soup=soup,
    )

    with patch.object(SceScraper, "load_scraper_config") as mock_cfg:
        mock_cfg.return_value = MagicMock(
            base_url="https://www.sce.ac.il", rate_limit=1.0,
            retries=1, proxy=None, directories=["/academic-units1/"],
        )
        scraper = SceScraper.__new__(SceScraper)
        scraper.source_slug = "sce"
        from scrapers.common.logger_manager import scraper_logger
        scraper.logger = scraper_logger.get_child("sce")
        result = await scraper.parse_page(ctx)

    assert len(result) == 1
    assert result[0].institution_slug == "sce"
    assert result[0].degree_level == "ba"
```

- [ ] **Step 2: Run — expect failure**

```bash
python -m pytest scrapers/tests/test_parsers.py::test_sce_parse_page_returns_degree -v
```

- [ ] **Step 3: Create `scrapers/institutions/sce/__init__.py`** (empty)

- [ ] **Step 4: Create `scrapers/institutions/sce/consts.py`**

```python
SOURCE_SLUG = "sce"
INSTITUTION_SLUG = "sce"
BASE_URL = "https://www.sce.ac.il"

CAMPUS_ROOTS = [
    "/academic-units1/beersheva/",
    "/academic-units1/ashdod/",
]

PROGRAM_LINK_SELECTORS = [
    "a[href*='/academic-units1/']", ".department-link a",
    ".program-link a", "nav a[href*='/academic-units']",
]
PROGRAM_NAME_SELECTORS = ["h1", ".page-title", ".department-title", "h2"]
FACULTY_NAME_SELECTORS = [".department-faculty", "[class*='faculty']", ".breadcrumb li:nth-child(3)"]
DEGREE_LEVEL_SELECTORS = [".degree-level", ".degree-type", "[class*='degree']"]
DUAL_MAJOR_KEYWORDS = ["דו-חוגי", "combined"]
EXTENDED_KEYWORD = "מורחב"
```

- [ ] **Step 5: Create `scrapers/institutions/sce/config.yaml`**

```yaml
base_url: "https://www.sce.ac.il"
rate_limit: 1.0
directories:
  - "/academic-units1/beersheva/"
  - "/academic-units1/ashdod/"
retries: 3
```

- [ ] **Step 6: Create `scrapers/institutions/sce/scraper.py`**

```python
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from ...playwright_scraper import PlaywrightAbstractScraper
from ...models import PageContext, Degree, Course, Review
from .consts import (
    SOURCE_SLUG, INSTITUTION_SLUG, BASE_URL,
    PROGRAM_LINK_SELECTORS, PROGRAM_NAME_SELECTORS,
    FACULTY_NAME_SELECTORS, DEGREE_LEVEL_SELECTORS,
    DUAL_MAJOR_KEYWORDS, EXTENDED_KEYWORD,
)


class SceScraper(PlaywrightAbstractScraper):
    """
    Scrapes SCE (Sami Shamoon) programs via Playwright (403 on plain aiohttp).
    Two campuses: beersheva, ashdod.
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
                path = full.replace(BASE_URL, "")
                if path.count("/") >= 4 and full not in seen:
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

        parts = ctx.url.split("/")
        campus = parts[4] if len(parts) > 4 else ""

        return [Degree(
            institution_slug=INSTITUTION_SLUG,
            slug=slug,
            name_he=name_he,
            faculty_slug=faculty_slug,
            degree_level=self._normalize_degree(degree_raw or "ba"),
            is_dual_major=any(kw in name_he for kw in DUAL_MAJOR_KEYWORDS),
            is_extended=EXTENDED_KEYWORD in name_he,
            canonical_url=ctx.url,
            metadata={"campus": campus},
            source_slug=self.source_slug,
        )]
```

- [ ] **Step 7: Run — expect pass**

```bash
python -m pytest scrapers/tests/test_parsers.py::test_sce_parse_page_returns_degree -v
```

---

### Task 14: Run all tests green

- [ ] **Step 1: Run full test suite**

```bash
python -m pytest scrapers/tests/test_parsers.py -v
```

Expected: All tests PASS. If any fail, fix the `parse_page()` implementation for that scraper until all pass.

- [ ] **Step 2: Verify imports are clean**

```bash
python -c "
from scrapers.institutions.tau.scraper import TauInstitutionScraper
from scrapers.institutions.huji.scraper import HujiScraper
from scrapers.institutions.technion.scraper import TechnionScraper
from scrapers.institutions.bgu.scraper import BguScraper
from scrapers.institutions.biu.scraper import BiuScraper
from scrapers.institutions.haifa.scraper import HaifaScraper
from scrapers.institutions.reichman.scraper import ReichmanScraper
from scrapers.institutions.afeka.scraper import AfekaScraper
from scrapers.institutions.ono.scraper import OnoScraper
from scrapers.institutions.sce.scraper import SceScraper
from scrapers.thestudent.scraper import TheStudentScraper
from scrapers.study.scraper import StudyScraper
print('All imports OK')
"
```

Expected: `All imports OK`

- [ ] **Step 3: Trigger a quick live smoke test (optional — requires Docker stack running)**

```bash
docker compose -f infra/docker-compose.yml exec scraper_worker python -c "
import asyncio
from scrapers.institutions.afeka.scraper import AfekaScraper
scraper = AfekaScraper()
result = asyncio.run(scraper._scrape())
print(f'Afeka: {len(result.degrees)} degrees scraped')
"
```

Expected: `Afeka: N degrees scraped` where N >= 5. This confirms the real site is reachable and selectors produce results.

---

### Task 15: Commit all changes

- [ ] **Step 1: Check status**

```bash
git status
```

- [ ] **Step 2: Stage all scraper changes**

```bash
git add scrapers/
```

- [ ] **Step 3: Commit**

```bash
git commit -m "scrapers: fix URLs, add Playwright fallback, add 9 institution scrapers

- TheStudent: fix 404 (wrong /Degrees/ dir) -> 2-hop /Categories discovery
- TAU: fix 404 (tau.ac.il/he/faculties) -> go.tau.ac.il faculty areas; move to institutions/tau/
- Study: fix 403 (Cloudflare) -> PlaywrightAbstractScraper
- Add PlaywrightAbstractScraper for Cloudflare-protected sites
- Add institution scrapers: huji, technion, bgu, biu, haifa, reichman, afeka, ono, sce
- Add scrapers/tests/ with parse_page() unit tests for each institution"
```

---

## Selector Tuning Guide

The CSS selectors in each scraper are best-effort based on common patterns. After the first live run, check the logs:

```bash
docker compose -f infra/docker-compose.yml logs scraper_worker | grep -E "degrees|skipping|Failed"
```

If a scraper returns 0 degrees from a page that should have content:
1. Open the URL in a browser and inspect the HTML
2. Find the actual CSS class/element holding the program name
3. Update `PROGRAM_NAME_SELECTORS` in that scraper's `consts.py`
4. Re-run the live smoke test

The scraper's `parse_page()` returns `[]` if `name_he` is empty — that's the signal that selectors need tuning.
