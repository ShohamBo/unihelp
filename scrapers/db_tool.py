import psycopg
from psycopg.rows import dict_row

_ALLOWED_TABLES = frozenset({
    "programs_program",
    "programs_course",
    "reviews_reviewsnippet",
    "reviews_reviewsource",
    "reviews_rawscrape",
})


class BeautifulTools:
    """Direct PostgreSQL write layer for Maslul scrapers.

    Scrapers write directly to the Django-managed tables via psycopg;
    Django reads the same rows through its ORM.
    """

    def __init__(self, db_url: str, logger):
        self.conn = psycopg.connect(db_url)
        self.logger = logger

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            self.conn.rollback()
        self.conn.close()
        return False

    # ------------------------------------------------------------------ upsert helpers

    def upsert_many(self, table_name: str, data, conflict_cols: list[str], **kwargs):
        """Upsert dataclass instances — all non-conflict cols updated on conflict."""
        from dataclasses import asdict
        if not data:
            return
        self.upsert_many_dicts(table_name, [asdict(r) for r in data], conflict_cols, **kwargs)

    def upsert_by_fields(self, table_name: str, data, conflict_cols: list[str], update_fields: list[str]):
        """Upsert dataclass instances — only specified fields updated on conflict."""
        from dataclasses import asdict
        if not data:
            return
        self.upsert_many_dicts(table_name, [asdict(r) for r in data], conflict_cols, update_fields=update_fields)

    def upsert_for_historic_data(self, table_name: str, data, conflict_cols: list[str], merge_ops: dict[str, str]):
        """Upsert with per-column merge semantics (sum | greatest | least)."""
        from dataclasses import asdict
        if not data:
            return
        if table_name not in _ALLOWED_TABLES:
            raise ValueError(f"Table {table_name!r} not in allowed list")
        rows = [asdict(r) for r in data]
        cols = list(rows[0].keys())
        t = table_name
        ops = {
            "sum": lambda c: f"{t}.{c} + EXCLUDED.{c}",
            "greatest": lambda c: f"GREATEST({t}.{c}, EXCLUDED.{c})",
            "least": lambda c: f"LEAST({t}.{c}, EXCLUDED.{c})",
        }
        set_clause = ", ".join(f"{c} = {ops[op](c)}" for c, op in merge_ops.items())
        sql = (
            f"INSERT INTO {t} ({', '.join(cols)}) "
            f"VALUES ({', '.join(f'%({c})s' for c in cols)}) "
            f"ON CONFLICT ({', '.join(conflict_cols)}) DO UPDATE SET {set_clause}"
        )
        try:
            with self.conn.cursor() as cur:
                cur.executemany(sql, rows)
            self.conn.commit()
        except Exception:
            self.conn.rollback()
            raise

    def upsert_many_dicts(
        self,
        table_name: str,
        rows: list[dict],
        conflict_cols: list[str],
        update_fields: list[str] | None = None,
        conflict_constraint: str | None = None,
        conflict_where: str | None = None,
    ):
        """Upsert plain dicts — caller maps field names to DB column names.

        conflict_constraint: ON CONFLICT ON CONSTRAINT <name> (named constraints only).
        conflict_where: WHERE clause appended to the column-list target for partial indexes,
                        e.g. conflict_where="course_code > ''" for the partial course index.
        """
        if not rows:
            return
        if table_name not in _ALLOWED_TABLES:
            raise ValueError(f"Table {table_name!r} not in allowed list")
        cols = list(rows[0].keys())
        update_cols = update_fields or [c for c in cols if c not in conflict_cols]
        if conflict_constraint:
            conflict_clause = f"ON CONSTRAINT {conflict_constraint}"
        else:
            col_list = f"({', '.join(conflict_cols)})"
            if conflict_where:
                col_list += f" WHERE {conflict_where}"
            conflict_clause = col_list
        sql = (
            f"INSERT INTO {table_name} ({', '.join(cols)}) "
            f"VALUES ({', '.join(f'%({c})s' for c in cols)}) "
            f"ON CONFLICT {conflict_clause} DO UPDATE "
            f"SET {', '.join(f'{c} = EXCLUDED.{c}' for c in update_cols)}"
        )
        try:
            with self.conn.cursor() as cur:
                cur.executemany(sql, rows)
            self.conn.commit()
        except Exception:
            self.conn.rollback()
            raise

    # ------------------------------------------------------------------ FK resolution

    def get_program_id_by_slugs(self, institution_slug: str, slug: str) -> int | None:
        """Return programs_program.id for (institution_slug, slug), or None."""
        with self.conn.cursor() as cur:
            cur.execute(
                "SELECT id FROM programs_program WHERE institution_slug = %s AND slug = %s LIMIT 1",
                (institution_slug, slug),
            )
            row = cur.fetchone()
            return row[0] if row else None

    # ------------------------------------------------------------------ generic read

    def get_all_from_table(self, table_name: str, where_clause: str = "", params=None):
        """SELECT * with optional WHERE clause. where_clause must be a safe literal."""
        if table_name not in _ALLOWED_TABLES:
            raise ValueError(f"Table {table_name!r} not in allowed list")
        try:
            with self.conn.cursor(row_factory=dict_row) as cur:
                query = f"SELECT * FROM {table_name}"
                if where_clause:
                    query += f" WHERE {where_clause}"
                cur.execute(query, params)
                return cur.fetchall()
        except Exception as e:
            self.logger.error(f"Error querying {table_name}: {e}")
            raise
