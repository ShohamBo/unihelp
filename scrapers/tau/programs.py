import re
from typing import AsyncIterator
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from ..base_scraper import BaseProgramScraper
from ..models import ProgramData

BASE_URL = "https://www.tau.ac.il"
FACULTY_INDEX = "/he/faculties"
INSTITUTION_SLUG = "tau"


class TauProgramsScraper(BaseProgramScraper):
    """
    Scrapes TAU program catalog.
    Discover all faculty pages → enumerate programs per faculty → extract metadata.

    Note: TAU's Yedion (course catalog) uses ASP.NET ViewState for pagination —
    this scraper targets the static program listing pages, not the ViewState-gated ones.
    PDF course catalogs are flagged but not parsed here.
    """

    source_slug = "tau_programs"
    rate_limit_per_minute = 10.0

    async def discover_urls(self) -> AsyncIterator[str]:
        try:
            soup = await self.get_page_soup(urljoin(BASE_URL, FACULTY_INDEX))
        except Exception as e:
            self.logger.error(f"Failed to load faculty index: {e}")
            return

        seen = set()
        for link in soup.select("a[href]"):
            href = link.get("href", "")
            if not href or href in seen:
                continue
            # Faculty pages typically contain 'faculty' or 'school' or are under faculty subdomains
            if any(kw in href.lower() for kw in ["/faculty/", "/school/", "/dept/", "yedion"]):
                full = href if href.startswith("http") else urljoin(BASE_URL, href)
                seen.add(full)
                yield full

    async def scrape_url(self, url: str) -> dict:
        soup = await self.get_page_soup(url)

        faculty_name = ""
        for sel in ["h1", ".faculty-title", ".page-title"]:
            el = soup.select_one(sel)
            if el:
                faculty_name = el.get_text(strip=True)
                break

        programs = []
        for program_el in soup.select(".program-item, .degree-item, li.program, tr.program"):
            name_el = program_el.select_one("a, .program-name, td:first-child")
            if not name_el:
                continue

            name_he = name_el.get_text(strip=True)
            prog_url = name_el.get("href", "")
            if prog_url and not prog_url.startswith("http"):
                prog_url = urljoin(url, prog_url)

            degree_raw = self._extract_text_by_selectors(
                program_el, [".degree-level", ".degree-type", "td:nth-child(2)"]
            )
            degree_level = self._normalize_degree(degree_raw)

            is_dual = any(kw in name_he for kw in ["דו-חוגי", "דו חוגי", "dual"])
            is_extended = "מורחב" in name_he

            programs.append({
                "name_he": name_he,
                "degree_level": degree_level,
                "is_dual_major": is_dual,
                "is_extended": is_extended,
                "canonical_url": prog_url,
            })

        return {"url": url, "faculty_name": faculty_name, "programs": programs}

    def to_programs(self, raw: dict) -> list[ProgramData]:
        faculty_slug = self._slugify(raw.get("faculty_name", ""))
        results = []

        for p in raw.get("programs", []):
            name_he = p.get("name_he", "").strip()
            if not name_he:
                continue

            slug = self._slugify(name_he)
            if not slug:
                continue

            results.append(ProgramData(
                institution_slug=INSTITUTION_SLUG,
                slug=slug,
                name_he=name_he,
                faculty_slug=faculty_slug,
                degree_level=p.get("degree_level", "ba"),
                is_dual_major=p.get("is_dual_major", False),
                is_extended=p.get("is_extended", False),
                canonical_url=p.get("canonical_url", ""),
                metadata={"source_faculty_name": raw.get("faculty_name", "")},
                raw_catalog_data=p,
            ))

        return results

    @staticmethod
    def _extract_text_by_selectors(el: BeautifulSoup, selectors: list[str]) -> str:
        for sel in selectors:
            found = el.select_one(sel)
            if found:
                return found.get_text(strip=True)
        return ""

    @staticmethod
    def _normalize_degree(raw: str) -> str:
        raw = raw.lower()
        if any(kw in raw for kw in ["ראשון", "ba", "b.a", "b.sc", "bsc"]):
            return "ba"
        if any(kw in raw for kw in ["שני", "ma", "m.a", "m.sc", "msc"]):
            return "ma"
        if any(kw in raw for kw in ["דוקטורט", "phd", "ph.d"]):
            return "phd"
        return "ba"

    @staticmethod
    def _slugify(text: str) -> str:
        he_to_en = {
            "א": "a", "ב": "b", "ג": "g", "ד": "d", "ה": "h", "ו": "v",
            "ז": "z", "ח": "ch", "ט": "t", "י": "y", "כ": "k", "ך": "k",
            "ל": "l", "מ": "m", "ם": "m", "נ": "n", "ן": "n", "ס": "s",
            "ע": "a", "פ": "p", "ף": "p", "צ": "ts", "ץ": "ts", "ק": "k",
            "ר": "r", "ש": "sh", "ת": "t",
        }
        result = ""
        for char in text.lower():
            if char in he_to_en:
                result += he_to_en[char]
            elif char.isascii() and char.isalnum():
                result += char
            elif char in (" ", "-", "_"):
                result += "-"
        result = re.sub(r"-+", "-", result).strip("-")
        return result[:80]
