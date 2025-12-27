"""Job processor - background task processing orchestration."""
import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from nanoid import generate

from src.domain.models.job import (
    CommandLog,
    CommandStatus,
    Job,
    JobMode,
    JobStatus,
    MetricsResult,
)
from src.domain.models.metrics import VideoInfo

logger = logging.getLogger(__name__)


def _now_tz():
    return datetime.now().astimezone()


def _make_command_callbacks(job, job_repository):
    def add_command_log(command_type: str, command: str, source_file: str = None) -> str:
        command_id = generate(size=8)
        log = CommandLog(
            command_id=command_id,
            command_type=command_type,
            command=command,
            status=CommandStatus.PENDING,
            source_file=source_file,
        )
        job.metadata.command_logs.append(log)
        job_repository.update_job(job)
        return command_id

    def update_command_status(command_id: str, status: str, error: str = None):
        for cmd_log in job.metadata.command_logs:
            if cmd_log.command_id == command_id:
                cmd_log.status = CommandStatus(status)
                now = _now_tz()
                if status == "running":
                    cmd_log.started_at = now
                elif status in ("completed", "failed"):
                    cmd_log.completed_at = now
                if error:
                    cmd_log.error_message = error
                break
        job_repository.update_job(job)

    return add_command_log, update_command_status


class TaskProcessor:
    """Background task processor."""

    def __init__(self) -> None:
        self.processing = False
        self.current_job: Optional[str] = None
        self.supported_modes = {JobMode.SINGLE_FILE, JobMode.DUAL_FILE, JobMode.BITSTREAM_ANALYSIS}

    async def process_job(self, job_id: str) -> None:
        """Process a single job."""
        from src.infrastructure.persistence import job_repository
        from src.infrastructure.ffmpeg.encoder import FFEncoder
        from src.infrastructure.ffmpeg.prober import FFProber
        from src.infrastructure.ffmpeg.metrics_calculator import MetricsCalculator
        from src.config import settings

        job = job_repository.get_job(job_id)
        if not job:
            logger.error(f"Job {job_id} not found")
            return

        if job.metadata.mode not in self.supported_modes:
            logger.info(f"Skipping job {job_id} (unsupported mode: {job.metadata.mode})")
            return

        encoder = FFEncoder(settings.get_ffmpeg_bin(), settings.ffmpeg_timeout)
        prober = FFProber(settings.get_ffprobe_bin())
        metrics_calc = MetricsCalculator(settings.get_ffmpeg_bin(), settings.ffmpeg_timeout)

        try:
            job.metadata.status = JobStatus.PROCESSING
            job.metadata.updated_at = _now_tz()
            job_repository.update_job(job)

            logger.info(f"Processing job {job_id} (mode: {job.metadata.mode})")

            if job.metadata.mode == JobMode.SINGLE_FILE:
                await self._process_single_file(job, encoder, prober, metrics_calc, job_repository)
            elif job.metadata.mode == JobMode.DUAL_FILE:
                await self._process_dual_file(job, prober, metrics_calc, job_repository)
            elif job.metadata.mode == JobMode.BITSTREAM_ANALYSIS:
                await self._process_bitstream_analysis(job, job_repository)

            job.metadata.status = JobStatus.COMPLETED
            job.metadata.completed_at = _now_tz()
            job.metadata.updated_at = _now_tz()
            job_repository.update_job(job)

            logger.info(f"Job {job_id} completed successfully")

        except Exception as e:
            job.metadata.status = JobStatus.FAILED
            job.metadata.error_message = str(e)
            job.metadata.updated_at = _now_tz()
            job_repository.update_job(job)

            logger.error(f"Job {job_id} failed: {str(e)}")

    async def _process_single_file(self, job: Job, encoder, prober, metrics_calc, job_repository) -> None:
        """Process single file mode job."""
        add_cmd, update_cmd = _make_command_callbacks(job, job_repository)

        reference_path = job.get_reference_path()
        if not reference_path or not reference_path.exists():
            raise FileNotFoundError(f"Reference video not found: {reference_path}")

        distorted_path = job.job_dir / "encoded_output.mp4"

        preset = job.metadata.preset or "medium"
        logger.info(f"Encoding video with preset: {preset}")

        await encoder.encode_video(
            input_path=reference_path,
            output_path=distorted_path,
            preset=preset,
            crf=23,
            add_command_callback=add_cmd,
            update_status_callback=update_cmd,
            command_type="encode",
            source_file=str(reference_path),
        )

        video_info = await prober.get_video_info(distorted_path)
        job.metadata.distorted_video = VideoInfo(
            filename=distorted_path.name,
            size_bytes=distorted_path.stat().st_size,
            **video_info,
        )

        await self._calculate_metrics(job, reference_path, distorted_path, metrics_calc, add_cmd, update_cmd, job_repository)

    async def _process_dual_file(self, job: Job, prober, metrics_calc, job_repository) -> None:
        """Process dual file mode job."""
        add_cmd, update_cmd = _make_command_callbacks(job, job_repository)

        reference_path = job.get_reference_path()
        distorted_path = job.get_distorted_path()

        if not reference_path or not reference_path.exists():
            raise FileNotFoundError(f"Reference video not found: {reference_path}")

        if not distorted_path or not distorted_path.exists():
            raise FileNotFoundError(f"Distorted video not found: {distorted_path}")

        ref_info = await prober.get_video_info(reference_path)
        dist_info = await prober.get_video_info(distorted_path)

        if ref_info["width"] != dist_info["width"] or ref_info["height"] != dist_info["height"]:
            logger.warning(
                f"Resolution mismatch: reference {ref_info['width']}x{ref_info['height']} vs "
                f"distorted {dist_info['width']}x{dist_info['height']}"
            )

        await self._calculate_metrics(job, reference_path, distorted_path, metrics_calc, add_cmd, update_cmd, job_repository)

    async def _process_bitstream_analysis(self, job: Job, job_repository) -> None:
        """Process bitstream analysis job."""
        from src.application.bitstream_analyzer import analyze_bitstream_job

        add_command_log, update_command_status = _make_command_callbacks(job, job_repository)

        report_data, summary = await analyze_bitstream_job(
            job,
            add_command_callback=add_command_log,
            update_status_callback=update_command_status,
        )

        report_rel_path = summary.get("report_data_file")
        if not report_rel_path:
            raise RuntimeError("Bitstream analysis missing report_data_file")

        report_path = job.job_dir / report_rel_path
        report_path.parent.mkdir(parents=True, exist_ok=True)
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report_data, f, ensure_ascii=False, indent=2)

        job.metadata.execution_result = summary
        job_repository.update_job(job)

    async def _calculate_metrics(
        self,
        job: Job,
        reference_path: Path,
        distorted_path: Path,
        metrics_calc,
        add_command_callback=None,
        update_status_callback=None,
        job_repository=None,
    ) -> None:
        """Calculate quality metrics."""
        metrics = MetricsResult()

        psnr_log = job.job_dir / "psnr.log"
        ssim_log = job.job_dir / "ssim.log"
        vmaf_json = job.job_dir / "vmaf.json"

        try:
            logger.info(f"Calculating metrics for job {job.job_id}")

            psnr_task = metrics_calc.calculate_psnr(
                reference_path, distorted_path, psnr_log,
                add_command_callback=add_command_callback,
                update_status_callback=update_status_callback,
                command_type="psnr",
                source_file=str(distorted_path),
            )
            ssim_task = metrics_calc.calculate_ssim(
                reference_path, distorted_path, ssim_log,
                add_command_callback=add_command_callback,
                update_status_callback=update_status_callback,
                command_type="ssim",
                source_file=str(distorted_path),
            )
            vmaf_task = metrics_calc.calculate_vmaf(
                reference_path, distorted_path, vmaf_json,
                add_command_callback=add_command_callback,
                update_status_callback=update_status_callback,
                command_type="vmaf",
                source_file=str(distorted_path),
            )

            psnr_result, ssim_result, vmaf_result = await asyncio.gather(
                psnr_task, ssim_task, vmaf_task, return_exceptions=True
            )

            if isinstance(psnr_result, dict):
                metrics.psnr_avg = psnr_result.get("psnr_avg")
                metrics.psnr_y = psnr_result.get("psnr_y")
                metrics.psnr_u = psnr_result.get("psnr_u")
                metrics.psnr_v = psnr_result.get("psnr_v")
            else:
                logger.error(f"PSNR calculation failed: {psnr_result}")

            if isinstance(ssim_result, dict):
                metrics.ssim_avg = ssim_result.get("ssim_avg")
                metrics.ssim_y = ssim_result.get("ssim_y")
                metrics.ssim_u = ssim_result.get("ssim_u")
                metrics.ssim_v = ssim_result.get("ssim_v")
            else:
                logger.error(f"SSIM calculation failed: {ssim_result}")

            if isinstance(vmaf_result, dict):
                metrics.vmaf_mean = vmaf_result.get("vmaf_mean")
                metrics.vmaf_harmonic_mean = vmaf_result.get("vmaf_harmonic_mean")
            else:
                logger.error(f"VMAF calculation failed: {vmaf_result}")

            job.metadata.metrics = metrics
            if job_repository:
                job_repository.update_job(job)

            logger.info(f"Metrics calculated successfully for job {job.job_id}")

        except Exception as e:
            logger.error(f"Failed to calculate metrics: {str(e)}")
            raise

    async def start_background_processor(self) -> None:
        """Start background processor (polls for pending jobs)."""
        from src.infrastructure.persistence import job_repository

        self.processing = True
        logger.info("Background task processor started")

        while self.processing:
            try:
                pending_jobs = job_repository.list_jobs(status=JobStatus.PENDING, limit=20)
                job_to_process = next(
                    (j for j in pending_jobs if j.metadata.mode in self.supported_modes),
                    None,
                )

                if job_to_process:
                    self.current_job = job_to_process.job_id
                    await self.process_job(job_to_process.job_id)
                    self.current_job = None
                else:
                    await asyncio.sleep(5)

            except Exception as e:
                logger.error(f"Error in background processor: {str(e)}")
                await asyncio.sleep(5)

    def stop_background_processor(self) -> None:
        """Stop background processor."""
        self.processing = False
        logger.info("Background task processor stopped")


# Global singleton
task_processor = TaskProcessor()
