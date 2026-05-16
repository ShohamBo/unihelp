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
