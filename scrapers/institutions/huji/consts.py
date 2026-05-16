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
