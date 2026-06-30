-- The two humans who use this system.
CREATE TABLE IF NOT EXISTS users (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    username     TEXT    NOT NULL UNIQUE,   -- 'ehesami' or 'jsamadi'
    email        TEXT    NOT NULL UNIQUE,
    display_name  TEXT    NOT NULL,
    password_hash TEXT    NOT NULL,
    created_at    TEXT    NOT NULL DEFAULT (datetime('now'))
);

-- One row per unique job posting, shared across users.
-- Dates stored as ISO text — SQLite has no native datetime type.
CREATE TABLE IF NOT EXISTS jobs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    source      TEXT    NOT NULL,           -- 'seek', 'linkedin', etc.
    source_id   TEXT    NOT NULL,           -- the ID the source assigned
    title       TEXT    NOT NULL,
    company     TEXT    NOT NULL,
    location    TEXT,
    description TEXT,
    url         TEXT,
    posted_at   TEXT,
    fetched_at  TEXT    NOT NULL DEFAULT (datetime('now')),
    expires_at  TEXT,                       -- from SEEK, null if unknown
    structured  TEXT,                       -- JSON: required_skills, seniority, etc.
    embedding   BLOB,                       -- sentence-transformer vector for pre-filtering
    is_active   INTEGER NOT NULL DEFAULT 1, -- 0 = stale, never deleted
    UNIQUE (source, source_id)              -- dedup key
);

-- One row per uploaded CV. The .docx is the source of truth; structured is the AI-extracted view.
CREATE TABLE IF NOT EXISTS cvs (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id        INTEGER NOT NULL REFERENCES users(id),
    filename       TEXT    NOT NULL,   -- original filename e.g. EhesamiJune26CV.docx
    stored_path    TEXT    NOT NULL,   -- path on disk relative to project root
    extracted_text TEXT,               -- plain text pulled from the .docx
    structured     TEXT,               -- JSON: skills, roles, work_history, etc.
    cv_embedding   BLOB,               -- sentence-transformer vector for pre-filtering
    is_current     INTEGER NOT NULL DEFAULT 1,  -- 1 = active CV for this user
    uploaded_at    TEXT    NOT NULL DEFAULT (datetime('now'))
);

-- Job titles each user wants to search for (e.g. "Data Engineer").
CREATE TABLE IF NOT EXISTS search_titles (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL REFERENCES users(id),
    title      TEXT    NOT NULL,
    is_active  INTEGER NOT NULL DEFAULT 1,
    created_at TEXT    NOT NULL DEFAULT (datetime('now')),
    UNIQUE (user_id, title)
);

-- Locations each user is willing to work in (e.g. "Melbourne", "Remote").
CREATE TABLE IF NOT EXISTS search_locations (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL REFERENCES users(id),
    location   TEXT    NOT NULL,
    is_active  INTEGER NOT NULL DEFAULT 1,
    created_at TEXT    NOT NULL DEFAULT (datetime('now')),
    UNIQUE (user_id, location)
);

-- One row per Claude API call, for cost and quality tracking.
CREATE TABLE IF NOT EXISTS llm_calls (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    called_at    TEXT    NOT NULL DEFAULT (datetime('now')),
    prompt_type  TEXT    NOT NULL,  -- 'cv_extraction' | 'job_extraction' | 'matcher'
    model        TEXT    NOT NULL,
    input_tokens  INTEGER NOT NULL,
    output_tokens INTEGER NOT NULL,
    cost_usd     REAL    NOT NULL,
    outcome      TEXT    NOT NULL,  -- 'success' | 'error'
    error_message TEXT              -- null on success
);

-- One row per full pipeline run.
CREATE TABLE IF NOT EXISTS pipeline_runs (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at     TEXT    NOT NULL DEFAULT (datetime('now')),
    finished_at    TEXT,
    jobs_fetched   INTEGER NOT NULL DEFAULT 0,
    jobs_new       INTEGER NOT NULL DEFAULT 0,
    jobs_rated     INTEGER NOT NULL DEFAULT 0,
    jobs_skipped   INTEGER NOT NULL DEFAULT 0,
    sources_failed INTEGER NOT NULL DEFAULT 0,
    status         TEXT    NOT NULL DEFAULT 'running'  -- 'running' | 'done' | 'failed'
);

-- Per-user ownership and personal state for each job.
-- A job appears here only when a user has seen/saved it.
CREATE TABLE IF NOT EXISTS user_jobs (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id  INTEGER NOT NULL REFERENCES users(id),
    job_id   INTEGER NOT NULL REFERENCES jobs(id),
    status       TEXT    NOT NULL DEFAULT 'new', -- new | reviewed | applied | rejected
    match_result TEXT,                           -- JSON: band, reasons, is_stretch, stretch_gap
    notes        TEXT,
    saved_at     TEXT    NOT NULL DEFAULT (datetime('now')),
    UNIQUE (user_id, job_id)
);
