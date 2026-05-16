SOURCE_SLUG = "thestudent"
BASE_URL = "https://www.thestudent.co.il"
CATEGORIES_INDEX = "/Categories"

MIN_REVIEW_LENGTH = 30

REVIEW_SELECTORS = [".review-item", ".student-review", "article.review", "div[class*='review']"]
REVIEW_TEXT_SELECTORS = [".review-text", ".review-body", "p.content", "p"]
REVIEW_DATE_SELECTORS = ["time", ".review-date", "[class*='date']"]
REVIEW_AUTHOR_SELECTORS = [".reviewer-name", ".author-name", "[class*='author']"]
PROGRAM_NAME_SELECTORS = ["h1", ".degree-title", ".page-title"]
