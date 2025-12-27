"""Job domain models."""
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from src.domain.models.metrics import MetricsResult, VideoInfo


class JobStatus(str, Enum):
    """Job status."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class JobMode(str, Enum):
    """Job mode."""

    SINGLE_FILE = "single_file"
    DUAL_FILE = "dual_file"
    BITSTREAM_ANALYSIS = "bitstream_analysis"
    COMPARISON = "comparison"
    TEMPLATE = "template"
    METRICS_ANALYSIS = "metrics_analysis"


class CommandStatus(str, Enum):
    """Command execution status."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class CommandLog(BaseModel):
    """Command execution log."""

    command_id: str
    command_type: str
    command: str
    status: CommandStatus = CommandStatus.PENDING
    source_file: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None


class JobMetadata(BaseModel):
    """Job metadata (persisted to JSON)."""

    job_id: str
    status: JobStatus = JobStatus.PENDING
    mode: JobMode

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None

    reference_video: Optional[VideoInfo] = None
    distorted_video: Optional[VideoInfo] = None
    encoded_videos: List[VideoInfo] = Field(default_factory=list)

    rawvideo_width: Optional[int] = None
    rawvideo_height: Optional[int] = None
    rawvideo_fps: Optional[float] = None
    rawvideo_pix_fmt: str = "yuv420p"

    preset: Optional[str] = None

    template_id: Optional[str] = None
    template_name: Optional[str] = None

    template_a_id: Optional[str] = None
    template_b_id: Optional[str] = None
    comparison_result: Optional[dict] = None

    execution_result: Optional[dict] = None

    command_logs: List[CommandLog] = Field(default_factory=list)

    metrics: Optional[MetricsResult] = None

    error_message: Optional[str] = None

    model_config = ConfigDict(json_encoders={datetime: lambda v: v.isoformat()})


class Job(BaseModel):
    """Job object (in-memory, includes file path)."""

    metadata: JobMetadata
    job_dir: Path

    model_config = ConfigDict(arbitrary_types_allowed=True)

    @property
    def job_id(self) -> str:
        return self.metadata.job_id

    @property
    def status(self) -> JobStatus:
        return self.metadata.status

    def get_reference_path(self) -> Optional[Path]:
        if self.metadata.reference_video:
            ref = Path(self.metadata.reference_video.filename)
            return ref if ref.is_absolute() else (self.job_dir / ref)
        return None

    def get_distorted_path(self) -> Optional[Path]:
        if self.metadata.distorted_video:
            dist = Path(self.metadata.distorted_video.filename)
            return dist if dist.is_absolute() else (self.job_dir / dist)
        return None

    def get_metadata_path(self) -> Path:
        return self.job_dir / "metadata.json"
