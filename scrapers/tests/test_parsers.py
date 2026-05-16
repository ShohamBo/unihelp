import pytest
from bs4 import BeautifulSoup
from unittest.mock import patch, MagicMock


def make_thestudent_review_html() -> str:
    return """
    <html><body>
      <h1 class="degree-title">משפטים</h1>
      <div class="review-item">
        <p class="review-text">לימודים מאתגרים מאוד, ממליץ בחום.</p>
        <time datetime="2024-03-01">מרץ 2024</time>
        <span class="reviewer-name">דנה כהן</span>
      </div>
      <div class="review-item">
        <p class="review-text">קורסים מגוונים ומרצים מעולים, שווה.</p>
      </div>
    </body></html>
    """


@pytest.mark.asyncio
async def test_thestudent_parse_page_returns_reviews():
    from scrapers.thestudent.scraper import TheStudentScraper
    from scrapers.models import PageContext, Review

    soup = BeautifulSoup(make_thestudent_review_html(), "html.parser")
    ctx = PageContext(url="https://www.thestudent.co.il/Degrees/Degree_1.html", html_soup=soup)

    with patch.object(TheStudentScraper, "load_scraper_config") as mock_cfg:
        mock_cfg.return_value = MagicMock(
            base_url="https://www.thestudent.co.il",
            rate_limit=1.0, retries=1, proxy=None, directories=["/Categories"]
        )
        scraper = TheStudentScraper.__new__(TheStudentScraper)
        scraper.source_slug = "thestudent"
        from scrapers.common.logger_manager import scraper_logger
        scraper.logger = scraper_logger.get_child("thestudent")

        result = await scraper.parse_page(ctx)

    assert len(result) == 2
    assert all(isinstance(r, Review) for r in result)
    assert result[0].degree_id == "mshptym"
    assert result[0].posted_at is not None
    assert result[0].author_handle == "דנה כהן"


def make_tau_program_html() -> str:
    return """
    <html><body>
      <h1 class="page-title">סטטיסטיקה ומדע הנתונים</h1>
      <div class="degree-level">תואר ראשון</div>
      <div class="faculty-name">מדעים מדויקים</div>
    </body></html>
    """


@pytest.mark.asyncio
async def test_tau_parse_page_returns_degree():
    from scrapers.institutions.tau.scraper import TauInstitutionScraper
    from scrapers.models import PageContext, Degree

    soup = BeautifulSoup(make_tau_program_html(), "html.parser")
    ctx = PageContext(
        url="https://go.tau.ac.il/he/exact/ba/statistics",
        html_soup=soup,
    )

    with patch.object(TauInstitutionScraper, "load_scraper_config") as mock_cfg:
        mock_cfg.return_value = MagicMock(
            base_url="https://go.tau.ac.il",
            rate_limit=1.0, retries=1, proxy=None,
            directories=["/he/exact"],
        )
        scraper = TauInstitutionScraper.__new__(TauInstitutionScraper)
        scraper.source_slug = "tau"
        from scrapers.common.logger_manager import scraper_logger
        scraper.logger = scraper_logger.get_child("tau")

        result = await scraper.parse_page(ctx)

    assert len(result) == 1
    deg = result[0]
    assert isinstance(deg, Degree)
    assert deg.institution_slug == "tau"
    assert deg.degree_level == "ba"
    assert deg.slug  # non-empty slug


def make_huji_program_html() -> str:
    return """
    <html><body>
      <h1 class="page-title">מדעי המחשב</h1>
      <div class="faculty-name">הפקולטה למדעים</div>
      <div class="degree-info">תואר ראשון - B.Sc</div>
    </body></html>
    """


@pytest.mark.asyncio
async def test_huji_parse_page_returns_degree():
    from scrapers.institutions.huji.scraper import HujiScraper
    from scrapers.models import PageContext, Degree

    soup = BeautifulSoup(make_huji_program_html(), "html.parser")
    ctx = PageContext(url="https://info.huji.ac.il/bachelor/Computer-Sciences", html_soup=soup)

    with patch.object(HujiScraper, "load_scraper_config") as mock_cfg:
        mock_cfg.return_value = MagicMock(
            base_url="https://info.huji.ac.il",
            rate_limit=1.0, retries=1, proxy=None,
            directories=["/courses/first-degree/faculty/all/grid/all"],
        )
        scraper = HujiScraper.__new__(HujiScraper)
        scraper.source_slug = "huji"
        from scrapers.common.logger_manager import scraper_logger
        scraper.logger = scraper_logger.get_child("huji")

        result = await scraper.parse_page(ctx)

    assert len(result) == 1
    deg = result[0]
    assert isinstance(deg, Degree)
    assert deg.institution_slug == "huji"
    assert deg.degree_level == "ba"


def make_technion_program_html() -> str:
    return """
    <html><body>
      <h1>הפקולטה למדעי המחשב</h1>
      <div class="program-info">
        <h2>תואר ראשון במדעי המחשב</h2>
        <p>תכנית לימודים רב-שנתית.</p>
      </div>
    </body></html>
    """


@pytest.mark.asyncio
async def test_technion_parse_page_returns_degree():
    from scrapers.institutions.technion.scraper import TechnionScraper
    from scrapers.models import PageContext, Degree

    soup = BeautifulSoup(make_technion_program_html(), "html.parser")
    ctx = PageContext(url="https://cs.technion.ac.il/he/undergraduate/", html_soup=soup)

    with patch.object(TechnionScraper, "load_scraper_config") as mock_cfg:
        mock_cfg.return_value = MagicMock(
            base_url="https://ugportal.technion.ac.il",
            rate_limit=1.0, retries=1, proxy=None,
            directories=[],
        )
        scraper = TechnionScraper.__new__(TechnionScraper)
        scraper.source_slug = "technion"
        from scrapers.common.logger_manager import scraper_logger
        scraper.logger = scraper_logger.get_child("technion")

        result = await scraper.parse_page(ctx)

    assert len(result) >= 1
    deg = result[0]
    assert isinstance(deg, Degree)
    assert deg.institution_slug == "technion"
    assert deg.degree_level == "ba"


def make_bgu_program_html() -> str:
    return """
    <html><body>
      <h1 class="program-title">מדעי המחשב</h1>
      <div class="faculty">הפקולטה למדעי המחשב</div>
      <div class="degree-type">תואר ראשון B.Sc</div>
    </body></html>
    """


@pytest.mark.asyncio
async def test_bgu_parse_page_returns_degree():
    from scrapers.institutions.bgu.scraper import BguScraper
    from scrapers.models import PageContext, Degree

    soup = BeautifulSoup(make_bgu_program_html(), "html.parser")
    ctx = PageContext(
        url="https://www.bgu.ac.il/welcome/ba/catalog/categories/computer-science/",
        html_soup=soup,
    )

    with patch.object(BguScraper, "load_scraper_config") as mock_cfg:
        mock_cfg.return_value = MagicMock(
            base_url="https://www.bgu.ac.il", rate_limit=1.0,
            retries=1, proxy=None, directories=["/welcome/ba/catalog/"],
        )
        scraper = BguScraper.__new__(BguScraper)
        scraper.source_slug = "bgu"
        from scrapers.common.logger_manager import scraper_logger
        scraper.logger = scraper_logger.get_child("bgu")
        result = await scraper.parse_page(ctx)

    assert len(result) == 1
    deg = result[0]
    assert isinstance(deg, Degree)
    assert deg.institution_slug == "bgu"
    assert deg.degree_level == "ba"


def make_biu_program_html() -> str:
    return """
    <html><body>
      <h1 class="page-title">פסיכולוגיה</h1>
      <div class="faculty-title">הפקולטה למדעי החברה</div>
      <div class="degree-level">תואר ראשון</div>
    </body></html>
    """


@pytest.mark.asyncio
async def test_biu_parse_page_returns_degree():
    from scrapers.institutions.biu.scraper import BiuScraper
    from scrapers.models import PageContext, Degree

    soup = BeautifulSoup(make_biu_program_html(), "html.parser")
    ctx = PageContext(url="https://www.biu.ac.il/catalog/psychology", html_soup=soup)

    with patch.object(BiuScraper, "load_scraper_config") as mock_cfg:
        mock_cfg.return_value = MagicMock(
            base_url="https://www.biu.ac.il", rate_limit=1.0,
            retries=1, proxy=None,
            directories=["/catalog/%D7%AA%D7%95%D7%90%D7%A8%20%D7%A8%D7%90%D7%A9%D7%95%D7%9F"],
        )
        scraper = BiuScraper.__new__(BiuScraper)
        scraper.source_slug = "biu"
        from scrapers.common.logger_manager import scraper_logger
        scraper.logger = scraper_logger.get_child("biu")
        result = await scraper.parse_page(ctx)

    assert len(result) == 1
    assert result[0].institution_slug == "biu"
    assert result[0].degree_level == "ba"


def make_haifa_program_html() -> str:
    return """
    <html><body>
      <h1 class="page-title">מדעי המחשב</h1>
      <div class="faculty-label">הפקולטה למדעי המחשב ומערכות מידע</div>
      <div class="degree-badge">תואר ראשון B.Sc</div>
    </body></html>
    """


@pytest.mark.asyncio
async def test_haifa_parse_page_returns_degree():
    from scrapers.institutions.haifa.scraper import HaifaScraper
    from scrapers.models import PageContext, Degree

    soup = BeautifulSoup(make_haifa_program_html(), "html.parser")
    ctx = PageContext(url="https://admissions.haifa.ac.il/computer-science/program/3210/", html_soup=soup)

    with patch.object(HaifaScraper, "load_scraper_config") as mock_cfg:
        mock_cfg.return_value = MagicMock(
            base_url="https://admissions.haifa.ac.il", rate_limit=1.0,
            retries=1, proxy=None, directories=["/bachelor/"],
        )
        scraper = HaifaScraper.__new__(HaifaScraper)
        scraper.source_slug = "haifa"
        from scrapers.common.logger_manager import scraper_logger
        scraper.logger = scraper_logger.get_child("haifa")
        result = await scraper.parse_page(ctx)

    assert len(result) == 1
    assert result[0].institution_slug == "haifa"
    assert result[0].degree_level == "ba"


def make_ono_program_html() -> str:
    return """
    <html><body>
      <h1 class="entry-title">משפטים - תואר ראשון LL.B</h1>
      <div class="faculty-name">הפקולטה למשפטים</div>
    </body></html>
    """


@pytest.mark.asyncio
async def test_ono_parse_page_returns_degree():
    from scrapers.institutions.ono.scraper import OnoScraper
    from scrapers.models import PageContext, Degree

    soup = BeautifulSoup(make_ono_program_html(), "html.parser")
    ctx = PageContext(url="https://www.ono.ac.il/curriculum/llb/", html_soup=soup)

    with patch.object(OnoScraper, "load_scraper_config") as mock_cfg:
        mock_cfg.return_value = MagicMock(
            base_url="https://www.ono.ac.il", rate_limit=1.0,
            retries=1, proxy=None, directories=["/curriculum/"],
        )
        scraper = OnoScraper.__new__(OnoScraper)
        scraper.source_slug = "ono"
        from scrapers.common.logger_manager import scraper_logger
        scraper.logger = scraper_logger.get_child("ono")
        result = await scraper.parse_page(ctx)

    assert len(result) == 1
    assert result[0].institution_slug == "ono"


def make_afeka_program_html() -> str:
    return """
    <html><body>
      <h1 class="page-title">הנדסת תוכנה</h1>
      <div class="degree-info">תואר ראשון B.Sc בהנדסת תוכנה</div>
    </body></html>
    """


@pytest.mark.asyncio
async def test_afeka_parse_page_returns_degree():
    from scrapers.institutions.afeka.scraper import AfekaScraper
    from scrapers.models import PageContext, Degree

    soup = BeautifulSoup(make_afeka_program_html(), "html.parser")
    ctx = PageContext(url="https://www.afeka.ac.il/academic-departments/bsc/software-engineering/", html_soup=soup)

    with patch.object(AfekaScraper, "load_scraper_config") as mock_cfg:
        mock_cfg.return_value = MagicMock(
            base_url="https://www.afeka.ac.il", rate_limit=1.0,
            retries=1, proxy=None, directories=["/academic-departments/bsc/"],
        )
        scraper = AfekaScraper.__new__(AfekaScraper)
        scraper.source_slug = "afeka"
        from scrapers.common.logger_manager import scraper_logger
        scraper.logger = scraper_logger.get_child("afeka")
        result = await scraper.parse_page(ctx)

    assert len(result) == 1
    assert result[0].institution_slug == "afeka"
    assert result[0].degree_level == "ba"


def make_reichman_program_html() -> str:
    return """
    <html><body>
      <h1 class="school-title">מדעי המחשב</h1>
      <div class="degree-type">תואר ראשון B.Sc</div>
      <div class="school-name">בית הספר למדעי המחשב</div>
    </body></html>
    """


@pytest.mark.asyncio
async def test_reichman_parse_page_returns_degree():
    from scrapers.institutions.reichman.scraper import ReichmanScraper
    from scrapers.models import PageContext, Degree

    soup = BeautifulSoup(make_reichman_program_html(), "html.parser")
    ctx = PageContext(url="https://www.runi.ac.il/he/schools/cs/", html_soup=soup)

    with patch.object(ReichmanScraper, "load_scraper_config") as mock_cfg:
        mock_cfg.return_value = MagicMock(
            base_url="https://www.runi.ac.il", rate_limit=1.0,
            retries=1, proxy=None, directories=["/he/schools/"],
        )
        scraper = ReichmanScraper.__new__(ReichmanScraper)
        scraper.source_slug = "reichman"
        from scrapers.common.logger_manager import scraper_logger
        scraper.logger = scraper_logger.get_child("reichman")
        result = await scraper.parse_page(ctx)

    assert len(result) == 1
    assert result[0].institution_slug == "reichman"
    assert result[0].degree_level == "ba"


def make_sce_program_html() -> str:
    return """
    <html><body>
      <h1 class="page-title">הנדסת תוכנה</h1>
      <div class="department-faculty">הנדסה</div>
      <div class="degree-level">תואר ראשון B.Sc</div>
    </body></html>
    """


@pytest.mark.asyncio
async def test_sce_parse_page_returns_degree():
    from scrapers.institutions.sce.scraper import SceScraper
    from scrapers.models import PageContext, Degree

    soup = BeautifulSoup(make_sce_program_html(), "html.parser")
    ctx = PageContext(
        url="https://www.sce.ac.il/academic-units1/ashdod/engineering/software-engineering",
        html_soup=soup,
    )

    with patch.object(SceScraper, "load_scraper_config") as mock_cfg:
        mock_cfg.return_value = MagicMock(
            base_url="https://www.sce.ac.il", rate_limit=1.0,
            retries=1, proxy=None, directories=["/academic-units1/"],
        )
        scraper = SceScraper.__new__(SceScraper)
        scraper.source_slug = "sce"
        from scrapers.common.logger_manager import scraper_logger
        scraper.logger = scraper_logger.get_child("sce")
        result = await scraper.parse_page(ctx)

    assert len(result) == 1
    assert result[0].institution_slug == "sce"
    assert result[0].degree_level == "ba"
