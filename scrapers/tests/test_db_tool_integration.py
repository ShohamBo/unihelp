"""
Integration tests for BeautifulTools against the real PostgreSQL container.

Requires: docker compose up db  (postgresql://maslul:maslul_dev@localhost:5432/maslul)
Run with: pytest scrapers/tests/test_db_tool_integration.py -v
"""
import logging
from datetime import datetime, timezone

import pytest
from psycopg.types.json import Jsonb

from scrapers.db_tool import BeautifulTools

TEST_DB_URL = "postgresql://maslul:maslul_dev@localhost:5432/maslul"
TEST_INSTITUTION_SLUG = "tau"
TEST_PROGRAM_SLUG = "pytest-cs-integration"
TEST_COURSE_CODE = "PYTEST-101"

log = logging.getLogger("test_integration")


# ------------------------------------------------------------------ fixtures


@pytest.fixture(scope="module")
def db():
    tool = BeautifulTools(TEST_DB_URL, logger=log)
    yield tool
    tool.conn.close()


@pytest.fixture(scope="module", autouse=True)
def cleanup(db):
    """Remove any leftover test data before and after the module."""
    def _wipe():
        with db.conn.cursor() as cur:
            cur.execute(
                "DELETE FROM programs_course WHERE program_id IN "
                "(SELECT id FROM programs_program WHERE slug = %s)",
                (TEST_PROGRAM_SLUG,),
            )
            cur.execute(
                "DELETE FROM programs_program WHERE slug = %s",
                (TEST_PROGRAM_SLUG,),
            )
        db.conn.commit()

    _wipe()
    yield
    _wipe()


# ------------------------------------------------------------------ upsert_many_dicts + get_program_id_by_slugs


def test_upsert_inserts_new_program(db):
    rows = [{
        "institution_slug": TEST_INSTITUTION_SLUG,
        "faculty_slug": "",
        "slug": TEST_PROGRAM_SLUG,
        "name_he": "מדעי המחשב אינטגרציה",
        "name_en": "CS Integration",
        "degree_level": "ba",
        "duration_years": 3.0,
        "total_credits": 120,
        "is_dual_major": False,
        "is_extended": False,
        "description_he": "",
        "canonical_url": "",
        "last_scraped_at": datetime.now(timezone.utc),
        "metadata": Jsonb({}),
    }]
    db.upsert_many_dicts(
        "programs_program", rows,
        conflict_cols=["institution_slug", "slug"],
    )
    pid = db.get_program_id_by_slugs(TEST_INSTITUTION_SLUG, TEST_PROGRAM_SLUG)
    assert pid is not None
    assert isinstance(pid, int)


def test_upsert_conflict_updates_name(db):
    pid_before = db.get_program_id_by_slugs(TEST_INSTITUTION_SLUG, TEST_PROGRAM_SLUG)
    rows = [{
        "institution_slug": TEST_INSTITUTION_SLUG,
        "faculty_slug": "",
        "slug": TEST_PROGRAM_SLUG,
        "name_he": "שם עודכן",
        "name_en": "Updated Name",
        "degree_level": "ba",
        "duration_years": 3.0,
        "total_credits": 120,
        "is_dual_major": False,
        "is_extended": False,
        "description_he": "",
        "canonical_url": "",
        "last_scraped_at": datetime.now(timezone.utc),
        "metadata": Jsonb({}),
    }]
    db.upsert_many_dicts(
        "programs_program", rows,
        conflict_cols=["institution_slug", "slug"],
        update_fields=["name_he", "name_en", "last_scraped_at"],
    )
    pid_after = db.get_program_id_by_slugs(TEST_INSTITUTION_SLUG, TEST_PROGRAM_SLUG)
    assert pid_after == pid_before

    from psycopg.rows import dict_row
    with db.conn.cursor(row_factory=dict_row) as cur:
        cur.execute("SELECT name_he FROM programs_program WHERE id = %s", (pid_after,))
        row = cur.fetchone()
    assert row["name_he"] == "שם עודכן"


# ------------------------------------------------------------------ get_program_id_by_slugs


def test_get_program_id_by_slugs_returns_none_for_unknown(db):
    assert db.get_program_id_by_slugs(TEST_INSTITUTION_SLUG, "this-slug-does-not-exist-9999") is None


# ------------------------------------------------------------------ upsert_many_dicts with partial constraint


def test_upsert_course_with_partial_index(db):
    program_id = db.get_program_id_by_slugs(TEST_INSTITUTION_SLUG, TEST_PROGRAM_SLUG)
    assert program_id is not None, "Run test_upsert_inserts_new_program first"

    rows = [{
        "program_id": program_id,
        "institution_slug": TEST_INSTITUTION_SLUG,
        "name_he": "מבוא למדעי המחשב",
        "name_en": "Intro to CS",
        "course_code": TEST_COURSE_CODE,
        "credits": 3,
        "semester": "א",
        "is_mandatory": True,
        "description_he": "",
        "metadata": Jsonb({}),
    }]
    db.upsert_many_dicts(
        "programs_course", rows,
        conflict_cols=["program_id", "course_code"],
        conflict_where="course_code > ''",
        update_fields=["name_he", "credits"],
    )

    with db.conn.cursor() as cur:
        cur.execute(
            "SELECT id, credits FROM programs_course WHERE course_code = %s AND program_id = %s",
            (TEST_COURSE_CODE, program_id),
        )
        row = cur.fetchone()
    assert row is not None
    assert row[1] == 3

    # Second upsert with updated credits — must update, not duplicate
    rows[0]["credits"] = 4
    db.upsert_many_dicts(
        "programs_course", rows,
        conflict_cols=["program_id", "course_code"],
        conflict_where="course_code > ''",
        update_fields=["name_he", "credits"],
    )
    with db.conn.cursor() as cur:
        cur.execute(
            "SELECT credits FROM programs_course WHERE course_code = %s AND program_id = %s",
            (TEST_COURSE_CODE, program_id),
        )
        row = cur.fetchone()
    assert row[0] == 4


# ------------------------------------------------------------------ upsert review snippet


def test_upsert_review_snippet(db):
    now = datetime.now(timezone.utc)

    rows = [{
        "source_slug": "pytest-test-source",
        "source_url": "https://example.com/review/1",
        "external_id": "pytest-ext-id-001",
        "raw_text": "לימודים מצוינים, ממליץ בחום",
        "language": "he",
        "posted_at": None,
        "scraped_at": now,
        "author_handle": "tester",
        "metadata": Jsonb({}),
    }]
    db.upsert_many_dicts(
        "reviews_reviewsnippet", rows,
        conflict_cols=["source_slug", "external_id"],
        update_fields=["raw_text", "author_handle", "metadata"],
    )

    from psycopg.rows import dict_row
    with db.conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            "SELECT raw_text, scraped_at FROM reviews_reviewsnippet "
            "WHERE source_slug = %s AND external_id = %s",
            ("pytest-test-source", "pytest-ext-id-001"),
        )
        row = cur.fetchone()
    assert row is not None
    assert row["raw_text"] == "לימודים מצוינים, ממליץ בחום"
    assert row["scraped_at"] is not None

    with db.conn.cursor() as cur:
        cur.execute(
            "DELETE FROM reviews_reviewsnippet WHERE source_slug = %s AND external_id = %s",
            ("pytest-test-source", "pytest-ext-id-001"),
        )
    db.conn.commit()


# ------------------------------------------------------------------ rollback on exception


def test_rollback_on_bad_insert(db):
    """A constraint violation must rollback and leave the connection usable."""
    bad_rows = [{"institution_slug": "x" * 200, "slug": "bad", "name_he": "x",
                 "name_en": "", "degree_level": "ba", "duration_years": None,
                 "faculty_slug": "", "total_credits": None, "is_dual_major": False,
                 "is_extended": False, "description_he": "", "canonical_url": "",
                 "last_scraped_at": None, "metadata": Jsonb({})}]
    with pytest.raises(Exception):
        db.upsert_many_dicts(
            "programs_program", bad_rows,
            conflict_cols=["institution_slug", "slug"],
        )

    # Connection must still be usable after the rollback
    result = db.get_program_id_by_slugs(TEST_INSTITUTION_SLUG, TEST_PROGRAM_SLUG)
    assert result is not None


# ------------------------------------------------------------------ table whitelist


def test_rejected_table_raises(db):
    with pytest.raises(ValueError, match="not in allowed list"):
        db.upsert_many_dicts("auth_user", [{"username": "x"}], conflict_cols=["username"])
