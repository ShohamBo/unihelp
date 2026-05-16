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
