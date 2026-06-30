import os
import sqlite3
from pathlib import Path

# In production, set DB_PATH env var to the Railway volume mount (e.g. /data/jobsearch.db).
# Locally it falls back to db/jobsearch.db.
DB_PATH = Path(os.environ.get("DB_PATH", str(Path(__file__).parent.parent / "db" / "jobsearch.db")))


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # access columns by name, not index
    return conn


def get_user(username: str):
    with get_connection() as conn:
        return conn.execute(
            "SELECT * FROM users WHERE username = ?", (username,)
        ).fetchone()


def get_search_titles(user_id: int):
    with get_connection() as conn:
        return conn.execute(
            "SELECT * FROM search_titles WHERE user_id = ? AND is_active = 1",
            (user_id,),
        ).fetchall()


def get_search_locations(user_id: int):
    with get_connection() as conn:
        return conn.execute(
            "SELECT * FROM search_locations WHERE user_id = ? AND is_active = 1",
            (user_id,),
        ).fetchall()


def add_search_title(user_id: int, title: str) -> None:
    with get_connection() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO search_titles (user_id, title) VALUES (?, ?)",
            (user_id, title),
        )


def add_search_location(user_id: int, location: str) -> None:
    with get_connection() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO search_locations (user_id, location) VALUES (?, ?)",
            (user_id, location),
        )


def deactivate_search_title(id: int, user_id: int) -> None:
    with get_connection() as conn:
        conn.execute(
            "UPDATE search_titles SET is_active = 0 WHERE id = ? AND user_id = ?",
            (id, user_id),
        )


def save_cv(user_id: int, filename: str, stored_path: str, extracted_text: str, structured: str) -> None:
    """Mark all previous CVs for this user as not current, then insert the new one."""
    with get_connection() as conn:
        conn.execute("UPDATE cvs SET is_current = 0 WHERE user_id = ?", (user_id,))
        conn.execute(
            """
            INSERT INTO cvs (user_id, filename, stored_path, extracted_text, structured)
            VALUES (?, ?, ?, ?, ?)
            """,
            (user_id, filename, stored_path, extracted_text, structured),
        )


def get_current_cv(user_id: int):
    """Return the current CV row for a user, or None."""
    with get_connection() as conn:
        return conn.execute(
            "SELECT * FROM cvs WHERE user_id = ? AND is_current = 1",
            (user_id,),
        ).fetchone()


def get_ranked_jobs(user_id: int) -> list:
    """Return all matched jobs for a user, sorted by band then date."""
    with get_connection() as conn:
        return conn.execute(
            """
            SELECT j.title, j.company, j.location, j.url, j.posted_at,
                   uj.match_result, uj.status
            FROM user_jobs uj
            JOIN jobs j ON j.id = uj.job_id
            WHERE uj.user_id = ? AND j.is_active = 1 AND uj.match_result IS NOT NULL
            ORDER BY
                CASE json_extract(uj.match_result, '$.band')
                    WHEN 'strong'   THEN 1
                    WHEN 'moderate' THEN 2
                    ELSE 3
                END,
                j.posted_at DESC
            """,
            (user_id,),
        ).fetchall()


def get_jobs_to_match(user_id: int) -> list:
    """Return active structured jobs not yet matched for this user."""
    with get_connection() as conn:
        return conn.execute(
            """
            SELECT j.id, j.title, j.company, j.structured, j.embedding
            FROM jobs j
            LEFT JOIN user_jobs uj ON uj.job_id = j.id AND uj.user_id = ?
            WHERE j.is_active = 1
              AND j.structured IS NOT NULL
              AND (uj.id IS NULL OR uj.match_result IS NULL)
            """,
            (user_id,),
        ).fetchall()


def save_match_result(user_id: int, job_id: int, match_result: str) -> None:
    """Upsert a user_jobs row with the match result."""
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO user_jobs (user_id, job_id, match_result)
            VALUES (?, ?, ?)
            ON CONFLICT (user_id, job_id) DO UPDATE SET match_result = excluded.match_result
            """,
            (user_id, job_id, match_result),
        )


def save_job_embedding(job_id: int, embedding: bytes) -> None:
    with get_connection() as conn:
        conn.execute("UPDATE jobs SET embedding = ? WHERE id = ?", (embedding, job_id))


def save_cv_embedding(cv_id: int, embedding: bytes) -> None:
    with get_connection() as conn:
        conn.execute("UPDATE cvs SET cv_embedding = ? WHERE id = ?", (embedding, cv_id))


def get_jobs_without_embedding() -> list:
    with get_connection() as conn:
        return conn.execute(
            "SELECT id, description FROM jobs WHERE is_active = 1 AND embedding IS NULL"
        ).fetchall()


def get_unstructured_jobs() -> list:
    """Return all active jobs that haven't been structured yet."""
    with get_connection() as conn:
        return conn.execute(
            "SELECT id, description FROM jobs WHERE is_active = 1 AND structured IS NULL"
        ).fetchall()


def save_job_structured(job_id: int, structured: str) -> None:
    """Save the extracted structured JSON for a job."""
    with get_connection() as conn:
        conn.execute(
            "UPDATE jobs SET structured = ? WHERE id = ?",
            (structured, job_id),
        )


def mark_stale_expired_jobs() -> int:
    """Set is_active=0 for any job whose expires_at has passed. Returns count updated."""
    with get_connection() as conn:
        cursor = conn.execute(
            """
            UPDATE jobs SET is_active = 0
            WHERE is_active = 1
              AND expires_at IS NOT NULL
              AND expires_at < datetime('now')
            """
        )
        return cursor.rowcount


def save_job(job: dict) -> int:
    """Insert a normalised job into the DB. Returns 1 if new, 0 if duplicate."""
    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT OR IGNORE INTO jobs
                (source, source_id, title, company, location, description, url, posted_at, expires_at)
            VALUES
                (:source, :source_id, :title, :company, :location, :description, :url, :posted_at, :expires_at)
            """,
            job,
        )
        return cursor.rowcount


def deactivate_search_location(id: int, user_id: int) -> None:
    with get_connection() as conn:
        conn.execute(
            "UPDATE search_locations SET is_active = 0 WHERE id = ? AND user_id = ?",
            (id, user_id),
        )


def start_pipeline_run() -> int:
    """Insert a new pipeline_runs row and return its id."""
    with get_connection() as conn:
        cursor = conn.execute(
            "INSERT INTO pipeline_runs (status) VALUES ('running')"
        )
        return cursor.lastrowid


def finish_pipeline_run(
    run_id: int,
    jobs_fetched: int,
    jobs_new: int,
    jobs_rated: int,
    jobs_skipped: int,
    sources_failed: int,
    status: str = "done",
) -> None:
    with get_connection() as conn:
        conn.execute(
            """
            UPDATE pipeline_runs
            SET finished_at    = datetime('now'),
                jobs_fetched   = ?,
                jobs_new       = ?,
                jobs_rated     = ?,
                jobs_skipped   = ?,
                sources_failed = ?,
                status         = ?
            WHERE id = ?
            """,
            (jobs_fetched, jobs_new, jobs_rated, jobs_skipped, sources_failed, status, run_id),
        )


def log_llm_call(
    prompt_type: str,
    model: str,
    input_tokens: int,
    output_tokens: int,
    cost_usd: float,
    outcome: str,
    error_message: str | None = None,
) -> None:
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO llm_calls
                (prompt_type, model, input_tokens, output_tokens, cost_usd, outcome, error_message)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (prompt_type, model, input_tokens, output_tokens, cost_usd, outcome, error_message),
        )
