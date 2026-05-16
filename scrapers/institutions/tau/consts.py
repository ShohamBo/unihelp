SOURCE_SLUG = "tau"
INSTITUTION_SLUG = "tau"
BASE_URL = "https://go.tau.ac.il"

import re
PROGRAM_LINK_RE = re.compile(r"^/he/[^/]+/(ba|ma)/[^/]+")

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
