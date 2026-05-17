import psycopg
from psycopg.rows import dict_row


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

    def upsert_many(self, table_name: str, data, conflict_cols: list[str]):
        """Upsert dataclass instances — all non-conflict cols updated on conflict."""
        from dataclasses import asdict
        if not data:
            return
        self.upsert_many_dicts(table_name, [asdict(r) for r in data], conflict_cols)

    def upsert_by_fields(self, table_name: str, data, conflict_cols: list[str], update_fields: list[str]):
        """Upsert dataclass instances — only specified fields updated on conflict."""
        from dataclasses import asdict
        if not data:
            return
        self.upsert_many_dicts(table_name, [asdict(r) for r in data], conflict_cols, update_fields)

    def upsert_for_historic_data(self, table_name: str, data, conflict_cols: list[str], merge_ops: dict[str, str]):
        """Upsert with per-column merge semantics (sum | greatest | least)."""
        from dataclasses import asdict
        if not data:
            return
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
    ):
        """Upsert plain dicts — caller maps field names to DB column names.

        conflict_constraint: use ON CONFLICT ON CONSTRAINT <name> instead of column list.
        """
        if not rows:
            return
        cols = list(rows[0].keys())
        update_cols = update_fields or [c for c in cols if c not in conflict_cols]
        if conflict_constraint:
            conflict_clause = f"ON CONSTRAINT {conflict_constraint}"
        else:
            conflict_clause = f"({', '.join(conflict_cols)})"
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

    def get_id_by_slug(self, table_name: str, slug: str) -> int | None:
        """Return the integer PK where slug = %s, or None."""
        with self.conn.cursor() as cur:
            cur.execute(f"SELECT id FROM {table_name} WHERE slug = %s LIMIT 1", (slug,))
            row = cur.fetchone()
            return row[0] if row else None

    def get_program_id(self, institution_id: int, slug: str) -> int | None:
        """Return programs_program.id for (institution_id, slug), or None."""
        with self.conn.cursor() as cur:
            cur.execute(
                "SELECT id FROM programs_program WHERE institution_id = %s AND slug = %s LIMIT 1",
                (institution_id, slug),
            )
            row = cur.fetchone()
            return row[0] if row else None

    def get_faculty_id(self, institution_id: int, faculty_slug: str) -> int | None:
        """Return institutions_faculty.id for (institution_id, slug), or None.

        Returns None for empty slug (faculty is nullable on Program).
        Logs a warning if a non-empty slug resolves to nothing.
        """
        if not faculty_slug:
            return None
        with self.conn.cursor() as cur:
            cur.execute(
                "SELECT id FROM institutions_faculty WHERE institution_id = %s AND slug = %s LIMIT 1",
                (institution_id, faculty_slug),
            )
            row = cur.fetchone()
        if row is None:
            self.logger.warning(f"Faculty slug {faculty_slug!r} not found for institution_id={institution_id}")
        return row[0] if row else None

    def get_or_create_review_source(self, name: str) -> int:
        """Return reviews_reviewsource.id for name, inserting a stub row if absent."""
        with self.conn.cursor() as cur:
            cur.execute("SELECT id FROM reviews_reviewsource WHERE name = %s LIMIT 1", (name,))
            row = cur.fetchone()
            if row:
                return row[0]
            cur.execute(
                "INSERT INTO reviews_reviewsource (name, base_url, is_active, rate_limit_per_minute) "
                "VALUES (%s, %s, %s, %s) RETURNING id",
                (name, "", True, 10),
            )
            source_id = cur.fetchone()[0]
        self.conn.commit()
        return source_id

    # ------------------------------------------------------------------ generic read

    def get_all_from_table(self, table_name: str, where_clause: str = "", params=None):
        """SELECT * with optional WHERE clause. where_clause must be a safe literal."""
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
