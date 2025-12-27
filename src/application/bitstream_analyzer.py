"""Bitstream analysis orchestration."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from src.config import settings
from src.domain.models.job import Job
from src.domain.services.metrics_parser import parse_psnr_log, parse_ssim_log, parse_vmaf_log
from src.infrastructure.ffmpeg.encoder import FFEncoder
from src.infrastructure.ffmpeg.prober import FFProber
from src.infrastructure.ffmpeg.runner import run_ffmpeg_command

logger = logging.getLogger(__name__)


def _is_yuv(path: Path) -> bool:
    return path.suffix.lower() == ".yuv"


def _frame_size_bytes_yuv420p(width: int, height: int) -> int:
    return (width * height * 3) // 2


def _count_yuv420p_frames(path: Path, width: int, height: int) -> int:
    frame_size = _frame_size_bytes_yuv420p(width, height)
    if frame_size <= 0:
        raise ValueError("Invalid frame size for yuv420p")
    size = path.stat().st_size
    if size % frame_size != 0:
        raise ValueError(f"YUV file size mismatch: {path.name}")
    return size // frame_size


class BitstreamAnalyzer:
    """Bitstream analysis service."""

    def __init__(self):
        self.encoder = FFEncoder(settings.get_ffmpeg_bin(), settings.ffmpeg_timeout)
        self.prober = FFProber(settings.get_ffprobe_bin())

    async def infer_input_format(self, path: Path) -> Optional[str]:
        """Infer input format from file."""
        if path.stat().st_size == 0:
            raise RuntimeError(f"File is empty: {path.name}")

        suffix = path.suffix.lower()
        if suffix in {".h264", ".264"}:
            return "h264"
        if suffix in {".h265", ".265", ".hevc"}:
            return "hevc"

        try:
            info = await self.prober.get_video_info(path)
            if info.get("width") and info.get("height"):
                return None
        except Exception:
            pass

        for fmt, codec in (("h264", "h264"), ("hevc", "hevc")):
            try:
                info = await self.prober.get_video_info(path, input_format=fmt)
                codec_name = info.get("codec_name")
                if info.get("width") and info.get("height") and codec_name == codec:
                    return fmt
            except Exception:
                continue

        raise RuntimeError(f"Cannot identify format: {path.name}")


async def build_bitstream_report(
    reference_path: Path,
    encoded_paths: List[Path],
    analysis_dir: Path,
    raw_width: Optional[int] = None,
    raw_height: Optional[int] = None,
    raw_fps: Optional[float] = None,
    raw_pix_fmt: str = "yuv420p",
    add_command_callback=None,
    update_status_callback=None,
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Build bitstream analysis report."""
    analyzer = BitstreamAnalyzer()
    encoder = analyzer.encoder
    prober = analyzer.prober

    analysis_dir.mkdir(parents=True, exist_ok=True)

    if not reference_path.exists():
        raise FileNotFoundError("Reference video not found")

    if not encoded_paths:
        raise ValueError("No encoded videos provided")

    # Prepare reference yuv420p
    ref_tmp_created = False
    if _is_yuv(reference_path):
        if raw_width is None or raw_height is None or raw_fps is None:
            raise ValueError("Reference is .yuv, must provide width/height/fps")
        ref_width, ref_height, ref_fps = raw_width, raw_height, float(raw_fps)
        ref_yuv = reference_path
    else:
        ref_fmt = await analyzer.infer_input_format(reference_path)
        ref_info = await prober.get_video_info(reference_path, input_format=ref_fmt)
        ref_width = int(ref_info.get("width") or 0)
        ref_height = int(ref_info.get("height") or 0)
        ref_fps_val = ref_info.get("fps")
        if not ref_width or not ref_height:
            raise ValueError("Cannot parse reference resolution")
        if not isinstance(ref_fps_val, (int, float)) or ref_fps_val <= 0:
            raise ValueError("Cannot parse reference fps")
        ref_fps = float(ref_fps_val)
        ref_yuv = analysis_dir / "ref_yuv420p.yuv"
        await encoder.decode_to_yuv420p(
            reference_path, ref_yuv,
            input_format=ref_fmt,
            add_command_callback=add_command_callback,
            update_status_callback=update_status_callback,
            command_type="ref_to_yuv",
            source_file=str(reference_path),
        )
        ref_tmp_created = True

    ref_frames_total = _count_yuv420p_frames(ref_yuv, ref_width, ref_height)

    async def _run_logged(cmd: List[str], cmd_type: str):
        await run_ffmpeg_command(
            cmd=cmd,
            timeout=settings.ffmpeg_timeout,
            add_command_callback=add_command_callback,
            update_status_callback=update_status_callback,
            command_type=cmd_type,
            source_file=str(reference_path),
            on_success=lambda: None,
            error_prefix=f"{cmd_type} failed",
        )

    encoded_reports: List[Dict[str, Any]] = []
    encoded_summaries: List[Dict[str, Any]] = []

    for idx, enc_input in enumerate(encoded_paths):
        if not enc_input.exists():
            raise FileNotFoundError(f"Encoded video not found: {enc_input.name}")

        enc_label = enc_input.name
        enc_is_yuv = _is_yuv(enc_input)

        enc_fmt: Optional[str] = None
        enc_codec: Optional[str] = None
        enc_width: Optional[int] = None
        enc_height: Optional[int] = None
        enc_fps: Optional[float] = None

        if enc_is_yuv:
            if raw_width is None or raw_height is None or raw_fps is None:
                raise ValueError("Encoded is .yuv, must provide width/height/fps")
            enc_width, enc_height, enc_fps = raw_width, raw_height, float(raw_fps)
        else:
            enc_fmt = await analyzer.infer_input_format(enc_input)
            info = await prober.get_video_info(enc_input, input_format=enc_fmt)
            enc_codec = info.get("codec_name")
            enc_width = int(info.get("width") or 0) if info.get("width") else None
            enc_height = int(info.get("height") or 0) if info.get("height") else None
            fps_val = info.get("fps")
            enc_fps = float(fps_val) if isinstance(fps_val, (int, float)) and fps_val > 0 else None

        if enc_fps is not None and abs(enc_fps - ref_fps) > 0.01:
            logger.warning(f"FPS mismatch: Ref={ref_fps}, Encoded({enc_label})={enc_fps}")
            enc_fps = ref_fps

        enc_yuv = analysis_dir / f"encoded_{idx+1}_yuv420p.yuv"

        scaled = False
        if enc_is_yuv:
            scaled = bool(enc_width != ref_width or enc_height != ref_height)
            if scaled:
                await encoder.decode_to_yuv420p(
                    enc_input, enc_yuv,
                    input_width=enc_width,
                    input_height=enc_height,
                    input_fps=ref_fps,
                    input_pix_fmt=raw_pix_fmt,
                    scale_width=ref_width,
                    scale_height=ref_height,
                    add_command_callback=add_command_callback,
                    update_status_callback=update_status_callback,
                    command_type="scale_yuv_to_ref",
                    source_file=str(enc_input),
                )
            else:
                enc_yuv = enc_input
        else:
            scaled = bool(enc_width and enc_height and (enc_width != ref_width or enc_height != ref_height))
            await encoder.decode_to_yuv420p(
                enc_input, enc_yuv,
                input_format=enc_fmt,
                scale_width=ref_width,
                scale_height=ref_height,
                add_command_callback=add_command_callback,
                update_status_callback=update_status_callback,
                command_type="bitstream_to_yuv",
                source_file=str(enc_input),
            )

        enc_frames = _count_yuv420p_frames(enc_yuv, ref_width, ref_height)
        frames_used = min(ref_frames_total, enc_frames)
        frame_mismatch = enc_frames != ref_frames_total

        psnr_log = analysis_dir / f"encoded_{idx+1}_psnr.log"
        ssim_log = analysis_dir / f"encoded_{idx+1}_ssim.log"
        vmaf_csv = analysis_dir / f"encoded_{idx+1}_vmaf.csv"

        ffmpeg_path = settings.get_ffmpeg_bin()
        raw_ref_args = [
            ffmpeg_path, "-y",
            "-f", "rawvideo", "-pix_fmt", "yuv420p",
            "-s", f"{ref_width}x{ref_height}", "-r", str(ref_fps),
            "-i", str(enc_yuv),
            "-f", "rawvideo", "-pix_fmt", "yuv420p",
            "-s", f"{ref_width}x{ref_height}", "-r", str(ref_fps),
            "-i", str(ref_yuv),
        ]

        limit_args = ["-frames:v", str(frames_used)] if frame_mismatch else []

        await _run_logged(
            raw_ref_args + ["-filter_complex", f"psnr=stats_file={psnr_log}"] + limit_args + ["-f", "null", "-"],
            "psnr",
        )
        await _run_logged(
            raw_ref_args + ["-filter_complex", f"ssim=stats_file={ssim_log}"] + limit_args + ["-f", "null", "-"],
            "ssim",
        )

        model_value = "version=vmaf_v0.6.1\\:name=vmaf|version=vmaf_v0.6.1neg\\:name=vmaf_neg"
        vmaf_filter = f"libvmaf='model={model_value}':n_threads=8:log_fmt=csv:log_path={vmaf_csv}"
        await _run_logged(
            raw_ref_args + ["-filter_complex", vmaf_filter] + limit_args + ["-f", "null", "-"],
            "vmaf",
        )

        psnr_data = parse_psnr_log(psnr_log)
        ssim_data = parse_ssim_log(ssim_log)
        vmaf_data = parse_vmaf_log(vmaf_csv)

        # Cleanup temp files
        try:
            if psnr_log.exists():
                psnr_log.unlink()
            if ssim_log.exists():
                ssim_log.unlink()
            if vmaf_csv.exists():
                vmaf_csv.unlink()
            if enc_yuv.exists() and enc_yuv != enc_input:
                enc_yuv.unlink()
        except Exception:
            logger.warning("Failed to cleanup temp files", exc_info=True)

        # Bitrate/frame structure
        frame_types: List[str] = []
        frame_sizes: List[int] = []
        frame_timestamps: List[float] = []

        if enc_is_yuv:
            frame_size = _frame_size_bytes_yuv420p(enc_width or ref_width, enc_height or ref_height)
            frame_types = ["RAW"] * frames_used
            frame_sizes = [frame_size] * frames_used
            frame_timestamps = [i / ref_fps for i in range(frames_used)]
        else:
            frames_info = await prober.probe_video_frames(enc_input, input_format=enc_fmt)
            for i, fr in enumerate(frames_info):
                frame_types.append(fr.get("pict_type") or "UNK")
                frame_sizes.append(int(fr.get("pkt_size") or 0))
                ts = fr.get("timestamp")
                frame_timestamps.append(float(ts) if ts is not None else (i / ref_fps))

            if len(frame_sizes) > frames_used:
                frame_types = frame_types[:frames_used]
                frame_sizes = frame_sizes[:frames_used]
                frame_timestamps = frame_timestamps[:frames_used]
            elif len(frame_sizes) < frames_used:
                frames_used = len(frame_sizes)

        duration_seconds = frames_used / ref_fps
        avg_bitrate_bps = int((sum(frame_sizes) * 8) / duration_seconds) if duration_seconds > 0 else 0

        encoded_reports.append({
            "label": enc_label,
            "format": enc_codec or "Unknown",
            "width": enc_width,
            "height": enc_height,
            "fps": enc_fps,
            "input_format": enc_fmt or "auto",
            "codec": enc_codec,
            "scaled_to_reference": scaled,
            "frames_total": enc_frames,
            "frames_used": frames_used,
            "frames_mismatch": frame_mismatch,
            "metrics": {"psnr": psnr_data, "ssim": ssim_data, "vmaf": vmaf_data},
            "bitrate": {
                "avg_bitrate_bps": avg_bitrate_bps,
                "frame_types": frame_types,
                "frame_sizes": frame_sizes,
                "frame_timestamps": frame_timestamps,
            },
        })

        encoded_summaries.append({
            "label": enc_label,
            "scaled_to_reference": scaled,
            "avg_bitrate_bps": avg_bitrate_bps,
            "psnr": psnr_data["summary"],
            "ssim": ssim_data["summary"],
            "vmaf": vmaf_data["summary"],
            "bitrate": {
                "frame_types": frame_types,
                "frame_sizes": frame_sizes,
                "frame_timestamps": [round(t, 2) for t in frame_timestamps],
            },
        })

    frames_used_overall = min(
        (item.get("frames_used", ref_frames_total) for item in encoded_reports),
        default=ref_frames_total,
    )

    report_data: Dict[str, Any] = {
        "kind": "bitstream_analysis",
        "reference": {
            "label": reference_path.name,
            "width": ref_width,
            "height": ref_height,
            "fps": ref_fps,
            "frames": ref_frames_total,
            "frames_total": ref_frames_total,
            "frames_used": frames_used_overall,
        },
        "encoded": encoded_reports,
    }

    summary: Dict[str, Any] = {
        "type": "bitstream_analysis",
        "reference": report_data["reference"],
        "encoded": encoded_summaries,
    }

    # Cleanup reference temp yuv
    try:
        if ref_tmp_created and ref_yuv.exists():
            ref_yuv.unlink()
    except Exception:
        logger.warning("Failed to cleanup reference yuv", exc_info=True)

    return report_data, summary


async def analyze_bitstream_job(
    job: Job,
    add_command_callback=None,
    update_status_callback=None,
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Execute bitstream analysis for a job."""
    ref_input = job.get_reference_path()
    if not ref_input or not ref_input.exists():
        raise FileNotFoundError("Reference video not found")

    analysis_dir = job.job_dir / "bitstream_analysis"
    encoded_inputs = [job.job_dir / v.filename for v in job.metadata.encoded_videos]
    if not encoded_inputs:
        raise ValueError("No encoded videos provided")

    raw_w = job.metadata.rawvideo_width
    raw_h = job.metadata.rawvideo_height
    raw_fps = job.metadata.rawvideo_fps
    raw_pix_fmt = job.metadata.rawvideo_pix_fmt or "yuv420p"

    report_data, summary = await build_bitstream_report(
        reference_path=ref_input,
        encoded_paths=encoded_inputs,
        analysis_dir=analysis_dir,
        raw_width=raw_w,
        raw_height=raw_h,
        raw_fps=raw_fps,
        raw_pix_fmt=raw_pix_fmt,
        add_command_callback=add_command_callback,
        update_status_callback=update_status_callback,
    )

    summary["report_data_file"] = str((analysis_dir / "report_data.json").relative_to(job.job_dir))
    report_data["job_id"] = job.job_id

    # Cleanup uploaded source files
    def _safe_unlink(path: Path) -> None:
        try:
            path.unlink()
        except FileNotFoundError:
            return
        except Exception:
            logger.warning(f"Failed to delete: {path}", exc_info=True)

    job_root = job.job_dir.resolve()
    to_remove: list[Path] = []

    ref_path = job.get_reference_path()
    if ref_path and ref_path.exists():
        try:
            if ref_path.resolve().is_relative_to(job_root):
                to_remove.append(ref_path)
        except Exception:
            pass

    for vid in job.metadata.encoded_videos or []:
        p = Path(vid.filename)
        if not p.is_absolute():
            p = job.job_dir / p
        if p.exists():
            try:
                if p.resolve().is_relative_to(job_root):
                    to_remove.append(p)
            except Exception:
                pass

    for item in to_remove:
        _safe_unlink(item)

    return report_data, summary
