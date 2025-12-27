"""Jobs API router."""
import os
import shutil
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, File, Form, HTTPException, Response, UploadFile

from src.domain.models.job import JobMetadata, JobMode, JobStatus
from src.infrastructure.filesystem import extract_video_info, save_uploaded_file
from src.infrastructure.persistence import job_repository
from src.interfaces.api.schemas.job import (
    CreateJobResponse,
    ErrorResponse,
    JobDetailResponse,
    JobListItem,
)

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


@router.post("", response_model=CreateJobResponse, status_code=201, responses={400: {"model": ErrorResponse}})
async def create_job(
    mode: str = Form(...),
    file: Optional[UploadFile] = File(None),
    reference: Optional[UploadFile] = File(None),
    distorted: Optional[UploadFile] = File(None),
    preset: Optional[str] = Form("medium"),
) -> CreateJobResponse:
    """Create new video quality analysis job."""
    try:
        job_mode = JobMode(mode)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid mode: {mode}")

    job_id = job_repository.generate_job_id()
    metadata = JobMetadata(job_id=job_id, status=JobStatus.PENDING, mode=job_mode)

    if job_mode == JobMode.SINGLE_FILE:
        if not file:
            raise HTTPException(status_code=400, detail="File required for single_file mode")
        metadata.preset = preset
        job = job_repository.create_job(metadata)
        file_content = await file.read()
        file_path = job.job_dir / file.filename
        save_uploaded_file(file_content, file_path)
        metadata.reference_video = extract_video_info(file_path)
        job_repository.update_job(job)

    elif job_mode == JobMode.DUAL_FILE:
        if not reference or not distorted:
            raise HTTPException(status_code=400, detail="Reference and distorted files required")
        job = job_repository.create_job(metadata)
        ref_content = await reference.read()
        ref_path = job.job_dir / reference.filename
        save_uploaded_file(ref_content, ref_path)
        metadata.reference_video = extract_video_info(ref_path)
        dist_content = await distorted.read()
        dist_path = job.job_dir / distorted.filename
        save_uploaded_file(dist_content, dist_path)
        metadata.distorted_video = extract_video_info(dist_path)
        job_repository.update_job(job)

    return CreateJobResponse(
        job_id=metadata.job_id,
        status=metadata.status,
        mode=metadata.mode,
        created_at=metadata.created_at,
    )


@router.get("/{job_id}", response_model=JobDetailResponse, responses={404: {"model": ErrorResponse}})
async def get_job(job_id: str) -> JobDetailResponse:
    """Get job details."""
    job = job_repository.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    m = job.metadata
    return JobDetailResponse(
        job_id=m.job_id,
        status=m.status,
        mode=m.mode,
        created_at=m.created_at,
        updated_at=m.updated_at,
        completed_at=m.completed_at,
        template_name=m.template_name,
        reference_filename=m.reference_video.filename if m.reference_video else None,
        distorted_filename=m.distorted_video.filename if m.distorted_video else None,
        preset=m.preset,
        metrics=m.metrics,
        command_logs=m.command_logs,
        error_message=m.error_message,
    )


@router.get("", response_model=List[JobListItem])
async def list_jobs(status: Optional[JobStatus] = None, limit: Optional[int] = None) -> List[JobListItem]:
    """List all jobs."""
    jobs = job_repository.list_jobs(status=status, limit=limit)
    return [
        JobListItem(
            job_id=j.metadata.job_id,
            status=j.metadata.status,
            mode=j.metadata.mode,
            created_at=j.metadata.created_at,
        )
        for j in jobs
    ]


def _unique_destination(directory: Path, filename: str) -> Path:
    safe_name = Path(filename).name
    candidate = directory / safe_name
    if not candidate.exists():
        return candidate
    stem, suffix = candidate.stem, candidate.suffix
    for idx in range(1, 1000):
        attempt = directory / f"{stem}_{idx}{suffix}"
        if not attempt.exists():
            return attempt
    raise RuntimeError(f"Failed to allocate unique filename for {safe_name}")


def _parse_paths_field(value: Optional[str]) -> List[Path]:
    if not value:
        return []
    items: List[Path] = []
    for line in value.replace(",", "\n").splitlines():
        stripped = line.strip()
        if stripped:
            items.append(Path(stripped).expanduser())
    return items


@router.post("/bitstream", response_model=CreateJobResponse, status_code=201, responses={400: {"model": ErrorResponse}})
async def create_bitstream_job(
    reference_path: Optional[str] = Form(None),
    encoded_paths: Optional[str] = Form(None),
    reference_file: Optional[UploadFile] = File(None),
    encoded_files: Optional[List[UploadFile]] = File(None),
    width: Optional[int] = Form(None),
    height: Optional[int] = Form(None),
    fps: Optional[float] = Form(None),
) -> CreateJobResponse:
    """Create bitstream analysis job."""
    ref_path = Path(reference_path).expanduser() if reference_path else None
    enc_path_list = _parse_paths_field(encoded_paths)

    if not reference_file and not ref_path:
        raise HTTPException(status_code=400, detail="Must provide reference_file or reference_path")
    if not encoded_files and not enc_path_list:
        raise HTTPException(status_code=400, detail="Must provide encoded_files or encoded_paths")

    if ref_path and (not ref_path.exists() or not ref_path.is_file()):
        raise HTTPException(status_code=400, detail=f"Reference path not found: {ref_path}")
    for p in enc_path_list:
        if not p.exists() or not p.is_file():
            raise HTTPException(status_code=400, detail=f"Encoded path not found: {p}")

    def _is_yuv(name: str) -> bool:
        return Path(name).suffix.lower() == ".yuv"

    has_yuv = False
    if reference_file and reference_file.filename and _is_yuv(reference_file.filename):
        has_yuv = True
    if ref_path and _is_yuv(ref_path.name):
        has_yuv = True
    if encoded_files:
        for f in encoded_files:
            if f.filename and _is_yuv(f.filename):
                has_yuv = True
                break
    for p in enc_path_list:
        if _is_yuv(p.name):
            has_yuv = True
            break

    if has_yuv and (width is None or height is None or fps is None):
        raise HTTPException(status_code=400, detail="YUV input requires width/height/fps")

    async def _read_upload(upload: Optional[UploadFile]):
        if not upload or not upload.filename:
            return None
        content = await upload.read()
        return (upload.filename, content) if content else None

    ref_upload = await _read_upload(reference_file)
    encoded_uploads = []
    if encoded_files:
        for upload in encoded_files:
            data = await _read_upload(upload)
            if data:
                encoded_uploads.append(data)

    if not ref_upload and not ref_path:
        raise HTTPException(status_code=400, detail="Must provide reference_file or reference_path")
    if not encoded_uploads and not enc_path_list:
        raise HTTPException(status_code=400, detail="Must provide encoded_files or encoded_paths")

    job_id = job_repository.generate_job_id()
    metadata = JobMetadata(
        job_id=job_id,
        mode=JobMode.BITSTREAM_ANALYSIS,
        status=JobStatus.PENDING,
        template_name="Bitstream Analysis",
        rawvideo_width=width,
        rawvideo_height=height,
        rawvideo_fps=fps,
    )
    job = job_repository.create_job(metadata)

    if ref_upload:
        ref_filename, ref_content = ref_upload
        ref_dest = _unique_destination(job.job_dir, ref_filename)
        save_uploaded_file(ref_content, ref_dest)
        metadata.reference_video = extract_video_info(ref_dest)
    else:
        metadata.reference_video = extract_video_info(ref_path)

    encoded_infos = []
    for filename, content in encoded_uploads:
        dest = _unique_destination(job.job_dir, filename)
        save_uploaded_file(content, dest)
        encoded_infos.append(extract_video_info(dest))
    for p in enc_path_list:
        encoded_infos.append(extract_video_info(p))

    metadata.encoded_videos = encoded_infos
    job_repository.update_job(job)

    return CreateJobResponse(
        job_id=metadata.job_id,
        status=metadata.status,
        mode=metadata.mode,
        created_at=metadata.created_at,
    )


@router.post("/compare", response_model=dict)
async def compare_jobs(job_ids: List[str]) -> dict:
    """Compare multiple jobs (removed)."""
    raise HTTPException(status_code=404, detail="Job comparison is removed")


@router.delete("/{job_id}", status_code=204, responses={404: {"model": ErrorResponse}})
async def delete_job(job_id: str) -> Response:
    """Delete job and related files."""
    job = job_repository.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    if not job_repository.delete_job(job_id):
        raise HTTPException(status_code=500, detail="Failed to delete job")
    return Response(status_code=204)
