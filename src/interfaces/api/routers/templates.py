"""Templates API router."""
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException
from nanoid import generate

from src.domain.models.job import CommandLog, CommandStatus, JobMetadata, JobMode, JobStatus
from src.domain.models.template import EncodingTemplateMetadata, TemplateSideConfig, TemplateType
from src.infrastructure.filesystem import dir_exists, dir_writable
from src.infrastructure.persistence import job_repository, template_repository
from src.application.template_executor import template_executor
from src.interfaces.api.schemas.template import (
    CreateTemplateRequest,
    CreateTemplateResponse,
    TemplateListItem,
    UpdateTemplateRequest,
    ValidateTemplateResponse,
)

router = APIRouter(prefix="/api/templates", tags=["templates"])


def _fingerprint(config: TemplateSideConfig) -> str:
    import hashlib
    data = f"{config.encoder_type}:{config.encoder_params}:{config.rate_control}:{sorted(config.bitrate_points)}"
    return hashlib.md5(data.encode()).hexdigest()[:8]


@router.post("", response_model=CreateTemplateResponse, status_code=201)
async def create_template(request: CreateTemplateRequest) -> CreateTemplateResponse:
    """Create new encoding template."""
    template_id = template_repository.generate_template_id()
    anchor_cfg = TemplateSideConfig(**request.anchor.model_dump())
    test_cfg = TemplateSideConfig(**request.test.model_dump())

    metadata = EncodingTemplateMetadata(
        template_id=template_id,
        name=request.name,
        description=request.description,
        anchor=anchor_cfg,
        test=test_cfg,
    )
    metadata.anchor_fingerprint = _fingerprint(metadata.anchor)

    try:
        template_repository.create_template(metadata)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return CreateTemplateResponse(template_id=template_id)


@router.get("/{template_id}")
async def get_template(template_id: str) -> dict:
    """Get template details."""
    template = template_repository.get_template(template_id)
    if not template:
        raise HTTPException(status_code=404, detail=f"Template {template_id} not found")
    return template.metadata.model_dump(mode="json")


@router.get("", response_model=List[TemplateListItem])
async def list_templates(limit: Optional[int] = None, template_type: Optional[TemplateType] = None) -> List[TemplateListItem]:
    """List all templates."""
    templates = template_repository.list_templates(limit=limit, template_type=template_type)
    return [
        TemplateListItem(
            template_id=t.metadata.template_id,
            name=t.metadata.name,
            description=t.metadata.description,
            created_at=t.metadata.created_at,
            template_type=t.metadata.template_type.value,
            anchor_source_dir=t.metadata.anchor.source_dir,
            anchor_bitstream_dir=t.metadata.anchor.bitstream_dir,
            test_source_dir=t.metadata.test.source_dir if t.metadata.test else None,
            test_bitstream_dir=t.metadata.test.bitstream_dir if t.metadata.test else None,
            anchor_computed=t.metadata.anchor_computed,
        )
        for t in templates
    ]


@router.put("/{template_id}")
async def update_template(template_id: str, request: UpdateTemplateRequest) -> dict:
    """Update template configuration."""
    template = template_repository.get_template(template_id)
    if not template:
        raise HTTPException(status_code=404, detail=f"Template {template_id} not found")

    anchor_changed = False
    if request.name is not None:
        template.metadata.name = request.name
    if request.description is not None:
        template.metadata.description = request.description
    if request.anchor is not None:
        template.metadata.anchor = TemplateSideConfig(**request.anchor.model_dump())
        anchor_changed = True
    if request.test is not None:
        template.metadata.test = TemplateSideConfig(**request.test.model_dump())

    if anchor_changed:
        template.metadata.anchor_computed = False
        template.metadata.anchor_fingerprint = _fingerprint(template.metadata.anchor)
        try:
            anchor_dir = Path(template.metadata.anchor.bitstream_dir)
            if anchor_dir.is_dir():
                for p in anchor_dir.iterdir():
                    if p.is_file():
                        p.unlink()
        except Exception:
            pass

    template_repository.update_template(template)
    return template.metadata.model_dump(mode="json")


@router.delete("/{template_id}", status_code=204)
async def delete_template(template_id: str) -> None:
    """Delete template."""
    if not template_repository.delete_template(template_id):
        raise HTTPException(status_code=404, detail=f"Template {template_id} not found")


@router.get("/{template_id}/validate", response_model=ValidateTemplateResponse)
async def validate_template(template_id: str) -> ValidateTemplateResponse:
    """Validate template paths."""
    template = template_repository.get_template(template_id)
    if not template:
        raise HTTPException(status_code=404, detail=f"Template {template_id} not found")

    b, e = template.metadata.anchor, template.metadata.test
    source_ok = dir_exists(b.source_dir) and dir_exists(e.source_dir)
    output_ok = dir_writable(b.bitstream_dir) and dir_writable(e.bitstream_dir)

    return ValidateTemplateResponse(
        template_id=template_id,
        source_exists=source_ok,
        output_dir_writable=output_ok,
        all_valid=source_ok and output_ok,
    )


@router.post("/{template_id}/execute", response_model=dict)
async def execute_template(template_id: str, background_tasks: BackgroundTasks) -> dict:
    """Execute template encoding."""
    template = template_repository.get_template(template_id)
    if not template:
        raise HTTPException(status_code=404, detail=f"Template {template_id} not found")

    job_id = job_repository.generate_job_id()
    metadata = JobMetadata(
        job_id=job_id,
        mode=JobMode.TEMPLATE,
        status=JobStatus.PENDING,
        template_a_id=template_id,
        template_name=template.metadata.name,
    )
    job = job_repository.create_job(metadata)

    async def execute_encoding():
        try:
            job.metadata.status = JobStatus.PROCESSING
            job_repository.update_job(job)

            result = await template_executor.execute(template, job=job)
            template_repository.update_template(template)

            job.metadata.execution_result = result
            job.metadata.status = JobStatus.FAILED if result.get("failed") else JobStatus.COMPLETED
            job.metadata.completed_at = datetime.utcnow()
            job_repository.update_job(job)
        except Exception as e:
            job.metadata.status = JobStatus.FAILED
            job.metadata.error_message = str(e)
            job_repository.update_job(job)

    background_tasks.add_task(execute_encoding)
    return {"job_id": job_id, "status": job.metadata.status.value, "message": "Task created"}


@router.post("/compare", response_model=dict)
async def compare_templates() -> dict:
    """Compare templates (removed)."""
    raise HTTPException(status_code=404, detail="Template compare is removed")
