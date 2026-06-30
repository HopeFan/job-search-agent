"""Creates jobsearch.db from schema.sql. Safe to re-run (uses IF NOT EXISTS)."""
from pathlib import Path
import sqlite3

DB_PATH = Path(__file__).parent / "jobsearch.db"
SCHEMA_PATH = Path(__file__).parent / "schema.sql"


def init_db() -> None:
    schema = SCHEMA_PATH.read_text()
    with sqlite3.connect(DB_PATH) as conn:
        conn.executescript(schema)
    print(f"Database ready: {DB_PATH}")


if __name__ == "__main__":
    init_db()
