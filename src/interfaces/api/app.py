"""FastAPI application setup."""
import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from src.config import settings
from src.shared.url_helpers import build_reports_base_url
from src.interfaces.api.routers import (
    jobs_router,
    metrics_analysis_router,
    pages_router,
    templates_router,
)
from src.application import task_processor


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage app startup/shutdown."""
    task = asyncio.create_task(task_processor.start_background_processor())
    yield
    task_processor.stop_background_processor()
    await task


app = FastAPI(
    title="VMA - Video Metrics Analyzer",
    description="Web application for video encoding quality analysis",
    version="0.1.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    lifespan=lifespan,
)

app.include_router(jobs_router)
app.include_router(pages_router)
app.include_router(templates_router)
app.include_router(metrics_analysis_router)

BASE_DIR = Path(__file__).resolve().parent.parent.parent
STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "templates"

if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

jinja_templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


@app.get("/", response_class=HTMLResponse)
async def root(request: Request) -> HTMLResponse:
    """Render index page."""
    return jinja_templates.TemplateResponse(
        "index.html",
        {"request": request, "recent_jobs": [], "reports_base_url": build_reports_base_url(request)},
    )


@app.get("/health")
async def health_check() -> dict:
    """Health probe."""
    return {"status": "healthy"}
