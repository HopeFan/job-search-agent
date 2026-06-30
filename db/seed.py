"""Insert the two app users. Safe to re-run (INSERT OR IGNORE)."""
from pathlib import Path
import sqlite3
import bcrypt

DB_PATH = Path(__file__).parent / "jobsearch.db"

USERS = [
    {
        "username": "ehesami",
        "email": "ehesami72@gmail.com",
        "display_name": "Erfan Hesami",
        "password": "9022127@",
    },
    {
        "username": "jsamadi",
        "email": "jsamadi@placeholder.com",  # update when confirmed
        "display_name": "J. Samadi",          # update when confirmed
        "password": "9022127@",
    },
]


def seed() -> None:
    with sqlite3.connect(DB_PATH) as conn:
        for u in USERS:
            conn.execute(
                """
                INSERT OR IGNORE INTO users (username, email, display_name, password_hash)
                VALUES (?, ?, ?, ?)
                """,
                (u["username"], u["email"], u["display_name"],
                 bcrypt.hashpw(u["password"].encode(), bcrypt.gensalt()).decode()),
            )
    print("Users seeded.")


if __name__ == "__main__":
    seed()
