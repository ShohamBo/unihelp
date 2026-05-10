SOURCE_SLUG = "study"
BASE_URL = "https://www.study.co.il"

MIN_REVIEW_LENGTH = 30

# Institution slugs mapped from study.co.il display names
INSTITUTION_NAME_MAP: dict[str, str] = {
    "אוניברסיטת תל אביב": "tau",
    "האוניברסיטה העברית": "huji",
    "הטכניון": "technion",
    "בן גוריון": "bgu",
    "אוניברסיטת בר-אילן": "biu",
    "אוניברסיטת חיפה": "haifa",
    "אוניברסיטת רייכמן": "reichman",
    "אפקה": "afeka",
}

PROGRAM_LINK_SELECTORS = ["a[href*='/degree/']", "a[href*='/program/']", "a[href*='/מסלול/']"]
REVIEW_SELECTORS = [".review", ".student-review", ".feedback-item", "article.review"]
REVIEW_TEXT_SELECTORS = [".review-content", ".review-text", ".review-body", "p"]
REVIEW_DATE_SELECTORS = ["time", ".date", "[class*='date']"]
PROGRAM_NAME_SELECTORS = ["h1", ".program-title", ".page-title", ".degree-title"]
INSTITUTION_NAME_SELECTORS = [".institution-name", ".university-name", "[class*='university']", "[class*='college']"]
