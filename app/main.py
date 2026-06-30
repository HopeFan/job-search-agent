import json
import os
from pathlib import Path
from zoneinfo import ZoneInfo

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from dotenv import load_dotenv
from fastapi import FastAPI, Form, Request, UploadFile, File
from fastapi.responses import RedirectResponse
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
)
from core.cv_extractor import extract_text, extract_structured
from core.embedder import embed

CV_STORE = Path(os.environ.get("CV_STORE_PATH", str(Path(__file__).parent.parent / "data" / "cvs")))
CV_STORE.mkdir(parents=True, exist_ok=True)

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
        request, "home.html", {"display_name": user["display_name"]}
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
            "title":       row["title"],
            "company":     row["company"],
            "location":    row["location"],
            "url":         row["url"],
            "band":        result["band"],
            "reasons":     result["reasons"],
            "is_stretch":  result.get("is_stretch", False),
            "stretch_gap": result.get("stretch_gap"),
        })

    return templates.TemplateResponse(request, "jobs.html", {"jobs": jobs})


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
