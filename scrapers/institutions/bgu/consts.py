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
