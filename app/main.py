import json
import os
import re
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from dotenv import load_dotenv
from fastapi import FastAPI, Form, Request, UploadFile, File
from fastapi.responses import RedirectResponse, FileResponse
from fastapi.templating import Jinja2Templates
import bcrypt
from starlette.middleware.sessions import SessionMiddleware

from app.database import (
    get_user,
    get_search_titles,
    get_search_locations,
    add_search_title,
    add_search_location,
    deactivate_search_title,
    deactivate_search_location,
    save_cv,
    save_cv_embedding,
    get_current_cv,
    get_ranked_jobs,
    get_job_match,
    save_tailored_cv,
    get_tailored_cvs_for_job,
    get_tailored_cv,
    get_total_cost,
    get_daily_costs,
    get_cost_by_prompt_type,
)
from core.cv_extractor import extract_text, extract_structured
from core.embedder import embed
from core.cv_tailor import propose_edits, apply_proposals
from docx import Document

CV_STORE = Path(os.environ.get("CV_STORE_PATH", str(Path(__file__).parent.parent / "data" / "cvs")))
CV_STORE.mkdir(parents=True, exist_ok=True)

TAILORED_CV_STORE = CV_STORE / "tailored"
TAILORED_CV_STORE.mkdir(parents=True, exist_ok=True)

load_dotenv()

app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key=os.environ["SECRET_KEY"])

templates = Jinja2Templates(directory=Path(__file__).parent / "templates")


def run_full_pipeline() -> None:
    from core.pipeline import run, extract_jobs, embed_jobs, match_jobs
    print("Scheduled pipeline starting...")
    run()
    extract_jobs()
    embed_jobs()
    match_jobs()
    print("Scheduled pipeline done.")


_scheduler = BackgroundScheduler()
_scheduler.add_job(
    run_full_pipeline,
    CronTrigger(hour=2, minute=0, timezone=ZoneInfo("Australia/Sydney")),
)


@app.on_event("startup")
def start_scheduler() -> None:
    _scheduler.start()


@app.on_event("shutdown")
def stop_scheduler() -> None:
    _scheduler.shutdown()


@app.get("/")
def home(request: Request):
    username = request.session.get("username")
    if not username:
        return RedirectResponse("/login", status_code=302)
    user = get_user(username)
    return templates.TemplateResponse(
        request, "home.html", {"display_name": user["display_name"], "username": username}
    )


@app.get("/login")
def login_page(request: Request):
    return templates.TemplateResponse(request, "login.html", {})


@app.post("/login")
def login(request: Request, username: str = Form(), password: str = Form()):
    user = get_user(username)
    if not user or not bcrypt.checkpw(password.encode(), user["password_hash"].encode()):
        return templates.TemplateResponse(
            request, "login.html", {"error": "Invalid username or password"}
        )
    request.session["username"] = user["username"]
    return RedirectResponse("/", status_code=302)


@app.get("/searches")
def searches_page(request: Request):
    username = request.session.get("username")
    if not username:
        return RedirectResponse("/login", status_code=302)
    user = get_user(username)
    return templates.TemplateResponse(request, "searches.html", {
        "titles": get_search_titles(user["id"]),
        "locations": get_search_locations(user["id"]),
    })


@app.post("/searches/titles")
def add_title(request: Request, title: str = Form()):
    username = request.session.get("username")
    if not username:
        return RedirectResponse("/login", status_code=302)
    user = get_user(username)
    add_search_title(user["id"], title.strip())
    return RedirectResponse("/searches", status_code=302)


@app.post("/searches/titles/{id}/remove")
def remove_title(request: Request, id: int):
    username = request.session.get("username")
    if not username:
        return RedirectResponse("/login", status_code=302)
    user = get_user(username)
    deactivate_search_title(id, user["id"])
    return RedirectResponse("/searches", status_code=302)


@app.post("/searches/locations")
def add_location(request: Request, location: str = Form()):
    username = request.session.get("username")
    if not username:
        return RedirectResponse("/login", status_code=302)
    user = get_user(username)
    add_search_location(user["id"], location.strip())
    return RedirectResponse("/searches", status_code=302)


@app.post("/searches/locations/{id}/remove")
def remove_location(request: Request, id: int):
    username = request.session.get("username")
    if not username:
        return RedirectResponse("/login", status_code=302)
    user = get_user(username)
    deactivate_search_location(id, user["id"])
    return RedirectResponse("/searches", status_code=302)


@app.get("/jobs")
def jobs_page(request: Request):
    username = request.session.get("username")
    if not username:
        return RedirectResponse("/login", status_code=302)
    user = get_user(username)
    raw_jobs = get_ranked_jobs(user["id"])

    jobs = []
    for row in raw_jobs:
        result = json.loads(row["match_result"])
        jobs.append({
            "id":          row["id"],
            "title":       row["title"],
            "company":     row["company"],
            "location":    row["location"],
            "url":         row["url"],
            "band":        result["band"],
            "reasons":     result["reasons"],
            "is_stretch":  result.get("is_stretch", False),
            "stretch_gap": result.get("stretch_gap"),
            "gap_suggestions": result.get("gap_suggestions", []),
        })

    return templates.TemplateResponse(request, "jobs.html", {"jobs": jobs})


@app.get("/jobs/{job_id}/tailor")
def tailor_cv_page(request: Request, job_id: int):
    username = request.session.get("username")
    if not username:
        return RedirectResponse("/login", status_code=302)
    user = get_user(username)

    job = get_job_match(user["id"], job_id)
    if not job:
        return RedirectResponse("/jobs", status_code=302)

    cv = get_current_cv(user["id"])
    if not cv:
        return RedirectResponse("/cv", status_code=302)

    gap_suggestions = json.loads(job["match_result"]).get("gap_suggestions", [])
    doc = Document(cv["stored_path"])
    proposals = propose_edits(doc, gap_suggestions)
    saved_versions = get_tailored_cvs_for_job(user["id"], job_id)

    return templates.TemplateResponse(request, "tailor_cv.html", {
        "job": job,
        "proposals": proposals,
        "saved_versions": saved_versions,
        "just_saved": request.query_params.get("saved") == "1",
    })


def _sanitize_for_filename(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "", text)


@app.post("/jobs/{job_id}/tailor")
async def tailor_cv_submit(request: Request, job_id: int):
    username = request.session.get("username")
    if not username:
        return RedirectResponse("/login", status_code=302)
    user = get_user(username)

    job = get_job_match(user["id"], job_id)
    if not job:
        return RedirectResponse("/jobs", status_code=302)

    cv = get_current_cv(user["id"])
    if not cv:
        return RedirectResponse("/cv", status_code=302)

    form = await request.form()
    proposal_count = int(form.get("proposal_count", 0))

    proposals = []
    for i in range(proposal_count):
        if form.get(f"include_{i}") != "on":
            continue
        proposals.append({
            "category": form[f"category_{i}"],
            "proposed_text": form[f"proposed_text_{i}"],
        })

    if not proposals:
        return RedirectResponse(f"/jobs/{job_id}/tailor", status_code=302)

    doc = Document(cv["stored_path"])
    apply_proposals(doc, proposals)

    filename = (
        f"{_sanitize_for_filename(user['display_name'])}_"
        f"{_sanitize_for_filename(job['title'])}_"
        f"{datetime.now().strftime('%Y%m%d')}.docx"
    )
    stored_path = TAILORED_CV_STORE / filename
    doc.save(stored_path)
    save_tailored_cv(user["id"], job_id, filename, str(stored_path))

    return RedirectResponse(f"/jobs/{job_id}/tailor?saved=1", status_code=302)


@app.get("/tailored-cv/{tailored_cv_id}/download")
def download_tailored_cv(request: Request, tailored_cv_id: int):
    username = request.session.get("username")
    if not username:
        return RedirectResponse("/login", status_code=302)
    user = get_user(username)

    tailored = get_tailored_cv(user["id"], tailored_cv_id)
    if not tailored:
        return RedirectResponse("/jobs", status_code=302)

    return FileResponse(
        tailored["stored_path"],
        filename=tailored["filename"],
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )


@app.get("/costs")
def costs_page(request: Request):
    username = request.session.get("username")
    if not username:
        return RedirectResponse("/login", status_code=302)
    if username != "ehesami":
        return RedirectResponse("/", status_code=302)

    return templates.TemplateResponse(request, "costs.html", {
        "total_cost": get_total_cost(),
        "daily": get_daily_costs(),
        "by_type": get_cost_by_prompt_type(),
    })


@app.get("/cv")
def cv_page(request: Request):
    username = request.session.get("username")
    if not username:
        return RedirectResponse("/login", status_code=302)
    user = get_user(username)
    current_cv = get_current_cv(user["id"])
    structured = None
    if current_cv and current_cv["structured"]:
        structured = json.dumps(json.loads(current_cv["structured"]), indent=2)
    return templates.TemplateResponse(request, "cv.html", {
        "current_cv": current_cv,
        "structured": structured,
    })


@app.post("/cv/upload")
async def cv_upload(request: Request, file: UploadFile = File(...)):
    username = request.session.get("username")
    if not username:
        return RedirectResponse("/login", status_code=302)
    user = get_user(username)

    if not file.filename.endswith(".docx"):
        return templates.TemplateResponse(request, "cv.html", {
            "current_cv": get_current_cv(user["id"]),
            "structured": None,
            "error": "Only .docx files are supported.",
        })

    stored_path = CV_STORE / f"{username}_{file.filename}"
    contents = await file.read()
    stored_path.write_bytes(contents)

    cv_text = extract_text(stored_path)
    structured = extract_structured(cv_text)

    save_cv(
        user_id=user["id"],
        filename=file.filename,
        stored_path=str(stored_path),
        extracted_text=cv_text,
        structured=json.dumps(structured),
    )
    cv = get_current_cv(user["id"])
    save_cv_embedding(cv["id"], embed(cv_text))
    return RedirectResponse("/cv", status_code=302)


@app.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/login", status_code=302)
