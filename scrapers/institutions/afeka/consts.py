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
