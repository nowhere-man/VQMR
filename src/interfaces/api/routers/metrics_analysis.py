"""Metrics analysis API router."""
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException

from src.domain.models.job import JobMetadata, JobMode, JobStatus
from src.domain.models.template import EncodingTemplateMetadata, TemplateSideConfig, TemplateType
from src.infrastructure.filesystem import dir_exists, dir_writable
from src.infrastructure.persistence import job_repository, template_repository
from src.application.template_executor import template_executor
from src.interfaces.api.schemas.metrics_analysis import (
    CreateMetricsTemplateRequest,
    MetricsTemplateListItem,
    UpdateMetricsTemplateRequest,
    ValidateMetricsTemplateResponse,
)

router = APIRouter(prefix="/api/metrics-analysis", tags=["metrics-analysis"])


@router.post("/templates", response_model=dict, status_code=201)
async def create_metrics_template(request: CreateMetricsTemplateRequest) -> dict:
    """Create metrics analysis template."""
    template_id = template_repository.generate_template_id()
    cfg = TemplateSideConfig(**request.config.model_dump())
    metadata = EncodingTemplateMetadata(
        template_id=template_id,
        name=request.name,
        description=request.description,
        template_type=TemplateType.METRICS_ANALYSIS,
        anchor=cfg,
        test=None,
    )
    try:
        template_repository.create_template(metadata)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"template_id": template_id, "status": "created"}


@router.get("/templates", response_model=List[MetricsTemplateListItem])
async def list_metrics_templates(limit: Optional[int] = None) -> List[MetricsTemplateListItem]:
    """List metrics analysis templates."""
    templates = template_repository.list_templates(limit=limit, template_type=TemplateType.METRICS_ANALYSIS)
    return [
        MetricsTemplateListItem(
            template_id=t.template_id,
            name=t.metadata.name,
            description=t.metadata.description,
            created_at=t.metadata.created_at,
            source_dir=t.metadata.anchor.source_dir,
            bitstream_dir=t.metadata.anchor.bitstream_dir,
            template_type=t.metadata.template_type.value,
        )
        for t in templates
    ]


@router.get("/templates/{template_id}")
async def get_metrics_template(template_id: str) -> dict:
    """Get metrics analysis template details."""
    template = template_repository.get_template(template_id)
    if not template or template.metadata.template_type != TemplateType.METRICS_ANALYSIS:
        raise HTTPException(status_code=404, detail=f"Template {template_id} not found")
    return template.metadata.model_dump(mode="json")


@router.put("/templates/{template_id}")
async def update_metrics_template(template_id: str, request: UpdateMetricsTemplateRequest) -> dict:
    """Update metrics analysis template."""
    template = template_repository.get_template(template_id)
    if not template or template.metadata.template_type != TemplateType.METRICS_ANALYSIS:
        raise HTTPException(status_code=404, detail=f"Template {template_id} not found")

    if request.name is not None:
        template.metadata.name = request.name
    if request.description is not None:
        template.metadata.description = request.description
    if request.config is not None:
        template.metadata.anchor = TemplateSideConfig(**request.config.model_dump())

    template_repository.update_template(template)
    return template.metadata.model_dump(mode="json")


@router.delete("/templates/{template_id}", status_code=204)
async def delete_metrics_template(template_id: str) -> None:
    """Delete metrics analysis template."""
    template = template_repository.get_template(template_id)
    if not template or template.metadata.template_type != TemplateType.METRICS_ANALYSIS:
        raise HTTPException(status_code=404, detail=f"Template {template_id} not found")
    template_repository.delete_template(template_id)


@router.get("/templates/{template_id}/validate", response_model=ValidateMetricsTemplateResponse)
async def validate_metrics_template(template_id: str) -> ValidateMetricsTemplateResponse:
    """Validate metrics template paths."""
    template = template_repository.get_template(template_id)
    if not template or template.metadata.template_type != TemplateType.METRICS_ANALYSIS:
        raise HTTPException(status_code=404, detail=f"Template {template_id} not found")

    c = template.metadata.anchor
    source_ok = dir_exists(c.source_dir)
    output_ok = dir_writable(c.bitstream_dir)

    return ValidateMetricsTemplateResponse(
        template_id=template_id,
        source_exists=source_ok,
        output_dir_writable=output_ok,
        all_valid=source_ok and output_ok,
    )


@router.post("/templates/{template_id}/execute", response_model=dict)
async def execute_metrics_template(template_id: str, background_tasks: BackgroundTasks) -> dict:
    """Execute metrics analysis template."""
    template = template_repository.get_template(template_id)
    if not template or template.metadata.template_type != TemplateType.METRICS_ANALYSIS:
        raise HTTPException(status_code=404, detail=f"Template {template_id} not found")

    job_id = job_repository.generate_job_id()
    metadata = JobMetadata(
        job_id=job_id,
        mode=JobMode.METRICS_ANALYSIS,
        status=JobStatus.PENDING,
        template_a_id=template_id,
        template_name=template.metadata.name,
    )
    job = job_repository.create_job(metadata)

    async def execute_task():
        try:
            job.metadata.status = JobStatus.PROCESSING
            job_repository.update_job(job)

            result = await template_executor.execute(template, job=job)
            job.metadata.execution_result = result
            job.metadata.status = JobStatus.FAILED if result.get("failed") else JobStatus.COMPLETED
            job.metadata.completed_at = datetime.utcnow()
            job_repository.update_job(job)
        except Exception as exc:
            job.metadata.status = JobStatus.FAILED
            job.metadata.error_message = str(exc)
            job_repository.update_job(job)

    background_tasks.add_task(execute_task)
    return {"job_id": job_id, "status": job.metadata.status.value, "message": "Metrics analysis task created"}
