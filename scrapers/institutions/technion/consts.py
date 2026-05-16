SOURCE_SLUG = "technion"
INSTITUTION_SLUG = "technion"
BASE_URL = "https://ugportal.technion.ac.il"

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
DUAL_MAJOR_KEYWORDS = ["דו-חוגי", "combined", "joint"]
EXTENDED_KEYWORD = "מורחב"
