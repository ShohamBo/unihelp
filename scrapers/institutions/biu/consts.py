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
