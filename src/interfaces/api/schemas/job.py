"""Job API schemas."""
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

from src.domain.models.job import CommandLog, JobMode, JobStatus
from src.domain.models.metrics import MetricsResult


class CreateJobResponse(BaseModel):
    """Create job response."""
    job_id: str
    status: JobStatus
    mode: JobMode
    created_at: datetime


class JobDetailResponse(BaseModel):
    """Job detail response."""
    job_id: str
    status: JobStatus
    mode: JobMode
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None
    template_name: Optional[str] = None
    reference_filename: Optional[str] = None
    distorted_filename: Optional[str] = None
    preset: Optional[str] = None
    metrics: Optional[MetricsResult] = None
    command_logs: List[CommandLog] = Field(default_factory=list)
    error_message: Optional[str] = None


class JobListItem(BaseModel):
    """Job list item."""
    job_id: str
    status: JobStatus
    mode: JobMode
    created_at: datetime


class MetricsResponse(BaseModel):
    """Metrics report response."""
    job_id: str
    status: JobStatus
    metrics: Optional[MetricsResult] = None


class ErrorResponse(BaseModel):
    """Error response."""
    detail: str
