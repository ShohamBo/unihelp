SOURCE_SLUG = "study"
BASE_URL = "https://www.study.co.il"

MIN_REVIEW_LENGTH = 30

INSTITUTION_NAME_MAP: dict[str, str] = {
    "אוניברסיטת תל אביב": "tau",
    "האוניברסיטה העברית": "huji",
    "הטכניון": "technion",
    "בן גוריון": "bgu",
    "אוניברסיטת בר-אילן": "biu",
    "אוניברסיטת חיפה": "haifa",
    "אוניברסיטת רייכמן": "reichman",
    "אפקה": "afeka",
    "אונו": "ono",
    "סמי שמעון": "sce",
}

PROGRAM_LINK_SELECTORS = [
    "a[href*='/P']", "a[href*='/degree/']",
    "a[href*='/program/']", ".program-card a", ".degree-link",
]
REVIEW_SELECTORS = [".review", ".student-review", ".feedback-item", "article.review", "[class*='review-']"]
REVIEW_TEXT_SELECTORS = [".review-content", ".review-text", ".review-body", "p.review", "p"]
REVIEW_DATE_SELECTORS = ["time", ".date", "[class*='date']", "[datetime]"]
PROGRAM_NAME_SELECTORS = ["h1", ".program-title", ".page-title", ".degree-title"]
INSTITUTION_NAME_SELECTORS = [
    ".institution-name", ".university-name",
    "[class*='university']", "[class*='college']", "[class*='institution']",
]
