from dataclasses import dataclass
from unittest.mock import MagicMock, patch

import pytest

from scrapers.db_tool import BeautifulTools


# ------------------------------------------------------------------ fixtures


def _make_cursor_cm(cursor):
    """Wrap a mock cursor in a context-manager shim."""
    cm = MagicMock()
    cm.__enter__ = MagicMock(return_value=cursor)
    cm.__exit__ = MagicMock(return_value=False)
    return cm


@pytest.fixture()
def cursor():
    return MagicMock()


@pytest.fixture()
def conn(cursor):
    c = MagicMock()
    c.cursor.return_value = _make_cursor_cm(cursor)
    return c


@pytest.fixture()
def db(conn):
    logger = MagicMock()
    with patch("psycopg.connect", return_value=conn):
        return BeautifulTools("postgresql://test/db", logger)


# ------------------------------------------------------------------ upsert_many_dicts


def test_upsert_many_dicts_executes_and_commits(db, conn, cursor):
    rows = [{"institution_slug": "tau", "slug": "cs", "name_he": "מדעי המחשב"}]
    db.upsert_many_dicts("programs_program", rows, conflict_cols=["institution_slug", "slug"])

    cursor.executemany.assert_called_once()
    sql, params = cursor.executemany.call_args[0]
    assert "INSERT INTO programs_program" in sql
    assert "ON CONFLICT (institution_slug, slug) DO UPDATE" in sql
    conn.commit.assert_called_once()


def test_upsert_many_dicts_empty_rows_is_noop(db, conn, cursor):
    db.upsert_many_dicts("programs_program", [], conflict_cols=["slug"])
    cursor.executemany.assert_not_called()
    conn.commit.assert_not_called()


def test_upsert_many_dicts_update_fields_subset(db, conn, cursor):
    rows = [{"institution_slug": "tau", "slug": "cs", "name_he": "מדעי המחשב", "name_en": "CS"}]
    db.upsert_many_dicts(
        "programs_program", rows,
        conflict_cols=["institution_slug", "slug"],
        update_fields=["name_he"],
    )
    sql, _ = cursor.executemany.call_args[0]
    do_update_clause = sql.split("DO UPDATE SET")[1]
    assert "name_he = EXCLUDED.name_he" in do_update_clause
    assert "name_en" not in do_update_clause
    assert "slug" not in do_update_clause


def test_upsert_many_dicts_uses_conflict_where_for_partial_index(db, conn, cursor):
    rows = [{"program_id": 1, "course_code": "CS101", "name_he": "אלגוריתמים"}]
    db.upsert_many_dicts(
        "programs_course", rows,
        conflict_cols=["program_id", "course_code"],
        conflict_where="course_code > ''",
    )
    sql, _ = cursor.executemany.call_args[0]
    assert "ON CONFLICT (program_id, course_code) WHERE course_code > '' DO UPDATE" in sql


def test_upsert_many_dicts_uses_constraint_name(db, conn, cursor):
    rows = [{"program_id": 1, "course_code": "CS101", "name_he": "אלגוריתמים"}]
    db.upsert_many_dicts(
        "programs_course", rows,
        conflict_cols=[],
        conflict_constraint="some_named_constraint",
    )
    sql, _ = cursor.executemany.call_args[0]
    assert "ON CONFLICT ON CONSTRAINT some_named_constraint DO UPDATE" in sql


def test_upsert_many_dicts_rollback_on_exception(db, conn, cursor):
    cursor.executemany.side_effect = Exception("DB error")
    with pytest.raises(Exception, match="DB error"):
        db.upsert_many_dicts(
            "programs_program",
            [{"slug": "cs"}],
            conflict_cols=["slug"],
        )
    conn.rollback.assert_called_once()
    conn.commit.assert_not_called()


def test_upsert_many_dicts_rejects_unknown_table(db):
    with pytest.raises(ValueError, match="not in allowed list"):
        db.upsert_many_dicts("auth_user", [{"slug": "x"}], conflict_cols=["slug"])


# ------------------------------------------------------------------ upsert_many (dataclass path)


def test_upsert_many_calls_upsert_many_dicts(db, conn, cursor):
    @dataclass
    class FakeRow:
        slug: str
        name_he: str

    rows = [FakeRow(slug="cs", name_he="מדעי המחשב")]
    db.upsert_many("programs_program", rows, conflict_cols=["slug"])

    cursor.executemany.assert_called_once()
    sql, params = cursor.executemany.call_args[0]
    assert "INSERT INTO programs_program" in sql
    assert params[0] == {"slug": "cs", "name_he": "מדעי המחשב"}


def test_upsert_many_empty_is_noop(db, conn, cursor):
    db.upsert_many("programs_program", [], conflict_cols=["slug"])
    cursor.executemany.assert_not_called()


# ------------------------------------------------------------------ get_program_id_by_slugs


def test_get_program_id_by_slugs_found(db, cursor):
    cursor.fetchone.return_value = (7,)
    assert db.get_program_id_by_slugs("tau", "cs") == 7
    _, params = cursor.execute.call_args[0]
    assert params == ("tau", "cs")


def test_get_program_id_by_slugs_not_found(db, cursor):
    cursor.fetchone.return_value = None
    assert db.get_program_id_by_slugs("tau", "cs") is None


# ------------------------------------------------------------------ get_all_from_table


def test_get_all_from_table_no_where(db, cursor):
    cursor.fetchall.return_value = [{"id": 1, "slug": "cs"}]
    result = db.get_all_from_table("programs_program")
    assert result == [{"id": 1, "slug": "cs"}]
    sql = cursor.execute.call_args[0][0]
    assert "WHERE" not in sql


def test_get_all_from_table_with_where(db, cursor):
    cursor.fetchall.return_value = []
    db.get_all_from_table("programs_program", where_clause="slug = %s", params=("cs",))
    sql, params = cursor.execute.call_args[0]
    assert "WHERE slug = %s" in sql
    assert params == ("cs",)


def test_get_all_from_table_propagates_exception(db, cursor):
    cursor.execute.side_effect = RuntimeError("connection lost")
    with pytest.raises(RuntimeError, match="connection lost"):
        db.get_all_from_table("programs_program")
    db.logger.error.assert_called_once()


def test_get_all_from_table_rejects_unknown_table(db):
    with pytest.raises(ValueError, match="not in allowed list"):
        db.get_all_from_table("django_migrations")


# ------------------------------------------------------------------ context manager


def test_context_manager_closes_connection_on_exit(conn):
    logger = MagicMock()
    with patch("psycopg.connect", return_value=conn):
        with BeautifulTools("postgresql://test/db", logger) as db:
            assert db.conn is conn
    conn.close.assert_called_once()
    conn.rollback.assert_not_called()


def test_context_manager_rollbacks_and_closes_on_exception(conn):
    logger = MagicMock()
    with patch("psycopg.connect", return_value=conn):
        with pytest.raises(ValueError, match="boom"):
            with BeautifulTools("postgresql://test/db", logger):
                raise ValueError("boom")
    conn.rollback.assert_called_once()
    conn.close.assert_called_once()
