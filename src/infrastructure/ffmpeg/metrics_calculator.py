"""FFmpeg metrics calculation (PSNR, SSIM, VMAF)."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from src.domain.services.metrics_parser import (
    parse_psnr_summary,
    parse_ssim_summary,
    parse_vmaf_summary,
)
from src.infrastructure.ffmpeg.runner import run_ffmpeg_command


class MetricsCalculator:
    """Calculate video quality metrics using FFmpeg."""

    def __init__(self, ffmpeg_path: str = "ffmpeg", timeout: int = 600):
        self.ffmpeg_path = ffmpeg_path
        self.timeout = timeout

    def _build_metric_cmd(
        self,
        reference_path: Path,
        distorted_path: Path,
        filter_str: str,
        ref_width: Optional[int] = None,
        ref_height: Optional[int] = None,
        ref_fps: Optional[float] = None,
        ref_pix_fmt: str = "yuv420p",
    ) -> List[str]:
        """Build metric calculation command."""
        cmd = [self.ffmpeg_path]

        cmd.extend(["-i", str(distorted_path)])

        if ref_width and ref_height:
            cmd.extend([
                "-f", "rawvideo",
                "-pix_fmt", ref_pix_fmt,
                "-s", f"{ref_width}x{ref_height}",
            ])
            if ref_fps:
                cmd.extend(["-r", str(ref_fps)])

        cmd.extend(["-i", str(reference_path)])
        cmd.extend(["-lavfi", filter_str, "-f", "null", "-"])

        return cmd

    async def _run_metric_cmd(
        self,
        cmd: List[str],
        metric_name: str,
        parse_func: Callable,
        output_path: Path,
        add_command_callback,
        update_status_callback,
        command_type: str,
        source_file: str,
    ) -> Dict[str, Any]:
        """Execute metric calculation command."""
        return await run_ffmpeg_command(
            cmd=cmd,
            timeout=self.timeout,
            add_command_callback=add_command_callback,
            update_status_callback=update_status_callback,
            command_type=command_type,
            source_file=source_file,
            on_success=lambda: parse_func(output_path),
            error_prefix=f"{metric_name} calculation failed",
        )

    async def calculate_psnr(
        self,
        reference_path: Path,
        distorted_path: Path,
        output_log: Path,
        ref_width: Optional[int] = None,
        ref_height: Optional[int] = None,
        ref_fps: Optional[float] = None,
        ref_pix_fmt: str = "yuv420p",
        add_command_callback=None,
        update_status_callback=None,
        command_type: str = "psnr",
        source_file: Optional[str] = None,
    ) -> Dict[str, float]:
        """Calculate PSNR metrics."""
        cmd = self._build_metric_cmd(
            reference_path, distorted_path,
            f"psnr=stats_file={output_log}",
            ref_width, ref_height, ref_fps, ref_pix_fmt,
        )
        return await self._run_metric_cmd(
            cmd, "PSNR", parse_psnr_summary, output_log,
            add_command_callback, update_status_callback,
            command_type, source_file or str(distorted_path),
        )

    async def calculate_ssim(
        self,
        reference_path: Path,
        distorted_path: Path,
        output_log: Path,
        ref_width: Optional[int] = None,
        ref_height: Optional[int] = None,
        ref_fps: Optional[float] = None,
        ref_pix_fmt: str = "yuv420p",
        add_command_callback=None,
        update_status_callback=None,
        command_type: str = "ssim",
        source_file: Optional[str] = None,
    ) -> Dict[str, float]:
        """Calculate SSIM metrics."""
        cmd = self._build_metric_cmd(
            reference_path, distorted_path,
            f"ssim=stats_file={output_log}",
            ref_width, ref_height, ref_fps, ref_pix_fmt,
        )
        return await self._run_metric_cmd(
            cmd, "SSIM", parse_ssim_summary, output_log,
            add_command_callback, update_status_callback,
            command_type, source_file or str(distorted_path),
        )

    async def calculate_vmaf(
        self,
        reference_path: Path,
        distorted_path: Path,
        output_json: Path,
        model_path: Optional[Path] = None,
        ref_width: Optional[int] = None,
        ref_height: Optional[int] = None,
        ref_fps: Optional[float] = None,
        ref_pix_fmt: str = "yuv420p",
        add_command_callback=None,
        update_status_callback=None,
        command_type: str = "vmaf",
        source_file: Optional[str] = None,
    ) -> Dict[str, float]:
        """Calculate VMAF metrics."""
        if model_path and model_path.exists():
            vmaf_filter = f"libvmaf=model_path={model_path}:log_path={output_json}:log_fmt=json"
        else:
            vmaf_filter = f"libvmaf=log_path={output_json}:log_fmt=csv"

        cmd = self._build_metric_cmd(
            reference_path, distorted_path,
            vmaf_filter,
            ref_width, ref_height, ref_fps, ref_pix_fmt,
        )
        return await self._run_metric_cmd(
            cmd, "VMAF", parse_vmaf_summary, output_json,
            add_command_callback, update_status_callback,
            command_type, source_file or str(distorted_path),
        )
