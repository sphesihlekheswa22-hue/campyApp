import asyncio
import os
from pathlib import Path

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.config import get_settings
from app.routers import (
    auth, users, companies, reports, extractions, analytics, governance, audit,
    notifications, scheduled_reports,
)

settings = get_settings()


async def _background_worker():
    from app.services.job_service import process_pending_jobs
    while True:
        try:
            processed = process_pending_jobs(limit=5)
            if processed:
                print(f"[WORKER] Processed {processed} job(s)")
        except Exception as e:
            print(f"[WORKER ERROR] {e}")
        await asyncio.sleep(settings.job_poll_seconds)


def _enqueue_due_scheduled_reports():
    from app.database.session import SessionLocal
    from app.services.job_service import enqueue_job
    from app.services.scheduled_report_service import due_schedules
    db = SessionLocal()
    try:
        for schedule in due_schedules(db):
            enqueue_job(db, "scheduled_report", {"schedule_id": schedule.id})
    finally:
        db.close()


def _enqueue_health_check():
    from app.database.session import SessionLocal
    from app.services.job_service import enqueue_job
    db = SessionLocal()
    try:
        enqueue_job(db, "health_check", {})
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.extraction.pipeline import recover_pending_extractions
    try:
        recover_pending_extractions()
    except Exception as e:
        print(f"[STARTUP] Extraction recovery skipped: {e}")

    worker_task = asyncio.create_task(_background_worker())

    scheduler = None
    try:
        from apscheduler.schedulers.asyncio import AsyncIOScheduler
        scheduler = AsyncIOScheduler()
        scheduler.add_job(_enqueue_due_scheduled_reports, "interval", hours=24, id="scheduled_reports")
        scheduler.add_job(_enqueue_health_check, "interval", hours=6, id="health_check")
        scheduler.start()
        print("[STARTUP] Scheduler started")
    except Exception as e:
        print(f"[STARTUP] Scheduler skipped: {e}")

    yield

    worker_task.cancel()
    if scheduler:
        scheduler.shutdown(wait=False)


app = FastAPI(title="JSE Analytics Platform", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

API_PREFIX = "/api"
app.include_router(auth.router, prefix=API_PREFIX)
app.include_router(users.router, prefix=API_PREFIX)
app.include_router(companies.router, prefix=API_PREFIX)
app.include_router(reports.router, prefix=API_PREFIX)
app.include_router(extractions.router, prefix=API_PREFIX)
app.include_router(analytics.router, prefix=API_PREFIX)
app.include_router(governance.router, prefix=API_PREFIX)
app.include_router(audit.router, prefix=API_PREFIX)
app.include_router(notifications.router, prefix=API_PREFIX)
app.include_router(scheduled_reports.router, prefix=API_PREFIX)

os.makedirs(settings.upload_dir, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=settings.upload_dir), name="uploads")

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"
if not FRONTEND_DIR.exists():
    FRONTEND_DIR = Path(__file__).resolve().parent.parent.parent / "frontend"

TEMPLATES_DIR = FRONTEND_DIR / "templates"
templates = Jinja2Templates(
    directory=str(TEMPLATES_DIR),
    auto_reload=settings.app_env == "development",
)

REDIRECT_HOME_ALIASES = {
    "",
    "index.html",
    "dashboard",
    "dashboard/index.html",
}

if FRONTEND_DIR.exists():
    app.mount("/css", StaticFiles(directory=str(FRONTEND_DIR / "css")), name="css")
    app.mount("/js", StaticFiles(directory=str(FRONTEND_DIR / "js")), name="js")
    if (FRONTEND_DIR / "assets").exists():
        app.mount("/assets", StaticFiles(directory=str(FRONTEND_DIR / "assets")), name="assets")


@app.get("/api/health")
def health():
    return {"status": "ok"}


def resolve_template(full_path: str) -> str | None:
    normalized = full_path.strip("/")
    if normalized in REDIRECT_HOME_ALIASES:
        return "redirect_home.html"

    candidates = [
        normalized,
        f"{normalized}/index.html" if not normalized.endswith(".html") else normalized,
        normalized if normalized.endswith(".html") else f"{normalized}.html",
    ]

    seen = set()
    for candidate in candidates:
        if not candidate or candidate in seen:
            continue
        seen.add(candidate)
        if candidate in REDIRECT_HOME_ALIASES:
            return "redirect_home.html"
        template_file = TEMPLATES_DIR / candidate
        if template_file.is_file():
            return candidate.replace("\\", "/")

    return None


@app.get("/")
async def root(request: Request):
    return templates.TemplateResponse("redirect_home.html", {"request": request})


@app.get("/{full_path:path}")
async def serve_frontend(request: Request, full_path: str):
    if full_path.startswith("api/"):
        return {"error": "Not found"}

    template_name = resolve_template(full_path)
    if template_name:
        return templates.TemplateResponse(template_name, {"request": request})

    return {"message": "JSE Analytics Platform API"}
