"""Creates jobsearch.db from schema.sql. Safe to re-run (uses IF NOT EXISTS).

CREATE TABLE IF NOT EXISTS only helps brand-new databases — if a table already
exists (e.g. in a deployed environment), SQLite skips it entirely, so columns
added to schema.sql later never reach that table on their own. NEW_COLUMNS
below is a hand-rolled migration list to cover that case: add an entry here
whenever schema.sql gains a column on a table that may already exist elsewhere.
"""
import os
from pathlib import Path
import sqlite3

DB_PATH = Path(os.environ.get("DB_PATH", str(Path(__file__).parent / "jobsearch.db")))
SCHEMA_PATH = Path(__file__).parent / "schema.sql"

NEW_COLUMNS = [
    ("user_jobs", "applied_at", "TEXT"),
    ("user_jobs", "emailed_at", "TEXT"),
    ("user_jobs", "messaged_at", "TEXT"),
    ("user_jobs", "tailored_cv_id", "INTEGER"),
]


def _add_missing_columns(conn: sqlite3.Connection) -> None:
    for table, column, coltype in NEW_COLUMNS:
        existing = {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}
        if column not in existing:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {coltype}")
            print(f"Added missing column: {table}.{column}")


def init_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    schema = SCHEMA_PATH.read_text()
    with sqlite3.connect(DB_PATH) as conn:
        conn.executescript(schema)
        _add_missing_columns(conn)
    print(f"Database ready: {DB_PATH}")


if __name__ == "__main__":
    init_db()
