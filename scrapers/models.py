from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class ScraperConfig:
    base_url: str
    rate_limit: float = 1.0  # requests per second
    directories: list[str] = field(default_factory=list)
    retries: int = 3
    proxy: str | None = None


@dataclass
class PageContext:
    url: str
    html_soup: object  # BeautifulSoup
    metadata: dict = field(default_factory=dict)


@dataclass
class ScraperResult:
    source_slug: str
    degrees: list["Degree"] = field(default_factory=list)
    courses: list["Course"] = field(default_factory=list)
    reviews: list["Review"] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


@dataclass
class Degree:
    """A university degree program (BA/MA/PhD) at a specific institution."""
    institution_slug: str
    slug: str
    name_he: str
    name_en: str = ""
    faculty_slug: str = ""
    degree_level: str = "ba"    # ba | ma | phd | other
    duration_years: float | None = None
    total_credits: int | None = None
    is_dual_major: bool = False
    is_extended: bool = False
    description_he: str = ""
    canonical_url: str = ""
    metadata: dict = field(default_factory=dict)
    source_slug: str = ""


@dataclass
class Course:
    """A single course within a degree program."""
    degree_id: str              # slug of the parent Degree
    institution_slug: str
    name_he: str
    name_en: str = ""
    course_code: str = ""
    credits: int | None = None
    semester: str = ""          # א | ב | שנתי
    is_mandatory: bool = True
    description_he: str = ""
    metadata: dict = field(default_factory=dict)


@dataclass
class Review:
    """A student review associated with a degree program."""
    degree_id: str              # slug of the related Degree (resolved by ProgramMapper)
    source_slug: str
    source_url: str
    source_id: str
    raw_text: str
    language: str = "he"
    posted_at: datetime | None = None
    author_handle: str = ""
    metadata: dict = field(default_factory=dict)
