"""Pages router - HTML page rendering."""
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from src.domain.models.job import JobStatus
from src.infrastructure.persistence import job_repository, template_repository
from src.shared.url_helpers import build_reports_base_url

router = APIRouter(tags=["pages"])

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
TEMPLATES_DIR = BASE_DIR / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


def _fmt_time(dt: Optional[datetime]) -> Optional[str]:
    if not dt:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    try:
        return dt.astimezone().strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return dt.strftime("%Y-%m-%d %H:%M:%S")


def _not_found_response(request: Request, resource_type: str, resource_id: str) -> HTMLResponse:
    return templates.TemplateResponse(
        "base.html",
        {"request": request, "reports_base_url": build_reports_base_url(request), "error": f"{resource_type} {resource_id} not found"},
        status_code=404,
    )


def _base_context(request: Request) -> dict:
    return {"request": request, "reports_base_url": build_reports_base_url(request)}


@router.get("/jobs/{job_id}", response_class=HTMLResponse)
async def job_report_page(request: Request, job_id: str) -> HTMLResponse:
    """Job report page."""
    job = job_repository.get_job(job_id)
    if not job:
        return _not_found_response(request, "Job", job_id)

    m = job.metadata
    context = _base_context(request)
    context["job"] = {
        "job_id": m.job_id,
        "status": m.status.value,
        "mode": m.mode.value,
        "created_at": _fmt_time(m.created_at),
        "updated_at": _fmt_time(m.updated_at),
        "completed_at": _fmt_time(m.completed_at),
        "template_name": m.template_name,
        "reference_filename": m.reference_video.filename if m.reference_video else None,
        "distorted_filename": m.distorted_video.filename if m.distorted_video else None,
        "encoded_filenames": [v.filename for v in (m.encoded_videos or [])],
        "preset": m.preset,
        "metrics": m.metrics,
        "error_message": m.error_message,
        "template_a_id": m.template_a_id,
        "template_b_id": m.template_b_id,
        "comparison_result": m.comparison_result,
        "execution_result": m.execution_result,
        "command_logs": [
            {
                "command_id": cmd.command_id,
                "command_type": cmd.command_type,
                "command": cmd.command,
                "status": cmd.status.value,
                "source_file": cmd.source_file,
                "started_at": cmd.started_at.isoformat() if cmd.started_at else None,
                "completed_at": cmd.completed_at.isoformat() if cmd.completed_at else None,
                "error_message": cmd.error_message,
            }
            for cmd in m.command_logs
        ],
    }
    return templates.TemplateResponse("job_report.html", context)


@router.get("/jobs", response_class=HTMLResponse)
async def jobs_list_page(request: Request, status: Optional[str] = None) -> HTMLResponse:
    """Jobs list page."""
    filter_status = None
    if status:
        try:
            filter_status = JobStatus(status)
        except ValueError:
            pass

    jobs = job_repository.list_jobs(status=filter_status)
    jobs_data = [
        {
            "job_id": j.metadata.job_id,
            "status": j.metadata.status.value,
            "template_name": j.metadata.template_name or "N/A",
            "created_at": _fmt_time(j.metadata.created_at) or "-",
            "completed_at": _fmt_time(j.metadata.completed_at) or "-",
            "error_message": j.metadata.error_message,
        }
        for j in jobs
    ]

    context = _base_context(request)
    context.update({"jobs": jobs_data, "status": status})
    return templates.TemplateResponse("jobs_list.html", context)


@router.get("/templates", response_class=HTMLResponse)
async def templates_list_page(request: Request) -> HTMLResponse:
    """Templates list page."""
    return templates.TemplateResponse("templates_list.html", _base_context(request))


@router.get("/templates/new", response_class=HTMLResponse)
async def create_template_page(request: Request) -> HTMLResponse:
    """Create new template page."""
    context = _base_context(request)
    context.update({"template_id": None, "readonly": False})
    return templates.TemplateResponse("template_form.html", context)


@router.get("/templates/{template_id}", response_class=HTMLResponse)
async def template_detail_page(request: Request, template_id: str) -> HTMLResponse:
    """Template detail page (readonly)."""
    template = template_repository.get_template(template_id)
    if not template:
        return _not_found_response(request, "Template", template_id)

    context = _base_context(request)
    context.update({"template_id": template_id, "readonly": True})
    return templates.TemplateResponse("template_form.html", context)


@router.get("/templates/{template_id}/edit", response_class=HTMLResponse)
async def edit_template_page(request: Request, template_id: str) -> HTMLResponse:
    """Edit template page."""
    template = template_repository.get_template(template_id)
    if not template:
        return _not_found_response(request, "Template", template_id)

    context = _base_context(request)
    context.update({"template_id": template_id, "readonly": False})
    return templates.TemplateResponse("template_form.html", context)


@router.get("/templates/{template_id}/view", response_class=HTMLResponse)
async def template_view_page(request: Request, template_id: str) -> HTMLResponse:
    """Template view page."""
    template = template_repository.get_template(template_id)
    if not template:
        return _not_found_response(request, "Template", template_id)

    context = _base_context(request)
    context.update({"template": template.metadata})
    return templates.TemplateResponse("template_view.html", context)


@router.get("/bitstream", response_class=HTMLResponse)
async def bitstream_analysis_page(request: Request) -> HTMLResponse:
    """Bitstream analysis page."""
    return templates.TemplateResponse("bitstream_analysis.html", _base_context(request))
