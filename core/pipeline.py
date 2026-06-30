"""Fetch pipeline — runs all saved searches for all users and stores jobs in the DB."""
import json
import sys
from app.database import (
    get_connection, get_search_titles, get_search_locations,
    save_job, mark_stale_expired_jobs,
    get_unstructured_jobs, save_job_structured,
    get_jobs_without_embedding, save_job_embedding, save_cv_embedding,
    get_current_cv, get_jobs_to_match, save_match_result,
    start_pipeline_run, finish_pipeline_run,
)
from core.seek_adapter import fetch_and_normalise
from core.job_extractor import extract_job_structured, strip_html
from core.matcher import rate_job
from core.embedder import embed, is_relevant


def run() -> None:
    run_id = start_pipeline_run()
    jobs_fetched = 0
    jobs_new = 0
    sources_failed = 0

    try:
        stale = mark_stale_expired_jobs()
        if stale:
            print(f"Marked {stale} expired job(s) as stale.")

        with get_connection() as conn:
            users = conn.execute("SELECT * FROM users").fetchall()

        for user in users:
            titles = get_search_titles(user["id"])
            locations = get_search_locations(user["id"])

            if not titles or not locations:
                print(f"[{user['username']}] No searches configured — skipping.")
                continue

            for t in titles:
                for loc in locations:
                    label = f"[{user['username']}] {t['title']} / {loc['location']}"
                    print(f"Fetching: {label}")
                    try:
                        jobs = fetch_and_normalise(t["title"], loc["location"])
                        jobs_fetched += len(jobs)
                        for job in jobs:
                            jobs_new += save_job(job)
                        print(f"  → {len(jobs)} fetched, {jobs_new} new so far")
                    except Exception as e:
                        sources_failed += 1
                        print(f"  → FAILED: {e}", file=sys.stderr)

        finish_pipeline_run(run_id, jobs_fetched, jobs_new, 0, 0, sources_failed)
    except Exception as e:
        finish_pipeline_run(run_id, jobs_fetched, jobs_new, 0, 0, sources_failed, status="failed")
        raise


def extract_jobs() -> None:
    """Extract structured data for any jobs that haven't been processed yet."""
    jobs = get_unstructured_jobs()
    if not jobs:
        print("All jobs already structured.")
        return
    print(f"Extracting structured data for {len(jobs)} job(s)...")
    for job in jobs:
        try:
            structured = extract_job_structured(job["description"] or "")
            save_job_structured(job["id"], json.dumps(structured))
        except Exception as e:
            print(f"  → Failed for job {job['id']}: {e}", file=sys.stderr)
    print("Done.")


def embed_jobs() -> None:
    """Compute and store embeddings for any jobs that don't have one yet."""
    jobs = get_jobs_without_embedding()
    if not jobs:
        print("All jobs already embedded.")
        return
    print(f"Embedding {len(jobs)} job(s)...")
    for job in jobs:
        text = strip_html(job["description"] or "")
        save_job_embedding(job["id"], embed(text))
    print("Done.")


def match_jobs() -> None:
    """Rate all unmatched jobs for every user who has a current CV."""
    with get_connection() as conn:
        users = conn.execute("SELECT * FROM users").fetchall()

    for user in users:
        cv = get_current_cv(user["id"])
        if not cv or not cv["structured"]:
            print(f"[{user['username']}] No CV — skipping matching.")
            continue

        cv_structured = json.loads(cv["structured"])

        # Embed CV if not already done
        cv_embedding = cv["cv_embedding"]
        if not cv_embedding:
            cv_embedding = embed(cv["extracted_text"] or "")
            save_cv_embedding(cv["id"], cv_embedding)

        jobs = get_jobs_to_match(user["id"])
        if not jobs:
            print(f"[{user['username']}] All jobs already matched.")
            continue

        print(f"[{user['username']}] {len(jobs)} job(s) to rate...")
        skipped = 0
        for job in jobs:
            # Pre-filter: skip jobs that are semantically too far from the CV
            if job["embedding"] and not is_relevant(job["embedding"], cv_embedding):
                skipped += 1
                continue
            try:
                result = rate_job(
                    cv_structured=cv_structured,
                    job_structured=json.loads(job["structured"]),
                    job_title=job["title"],
                    job_company=job["company"],
                )
                save_match_result(user["id"], job["id"], json.dumps(result))
                print(f"  [{result['band'].upper()}] {job['title']} @ {job['company']}")
            except Exception as e:
                print(f"  → Failed for job {job['id']}: {e}", file=sys.stderr)

        if skipped:
            print(f"  → {skipped} job(s) filtered out by embedding pre-filter.")


if __name__ == "__main__":
    run()
