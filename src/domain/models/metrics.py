"""Metrics domain models."""
from typing import Optional

from pydantic import BaseModel


class MetricsResult(BaseModel):
    """Video quality metrics result."""

    psnr_avg: Optional[float] = None
    psnr_y: Optional[float] = None
    psnr_u: Optional[float] = None
    psnr_v: Optional[float] = None

    ssim_avg: Optional[float] = None
    ssim_y: Optional[float] = None
    ssim_u: Optional[float] = None
    ssim_v: Optional[float] = None

    vmaf_mean: Optional[float] = None
    vmaf_harmonic_mean: Optional[float] = None

    frame_metrics_file: Optional[str] = None


class VideoInfo(BaseModel):
    """Video file information."""

    filename: str
    size_bytes: int
    duration: Optional[float] = None
    width: Optional[int] = None
    height: Optional[int] = None
    fps: Optional[float] = None
    bitrate: Optional[int] = None
