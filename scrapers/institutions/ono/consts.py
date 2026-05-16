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
