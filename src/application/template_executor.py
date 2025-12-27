"""Template execution orchestration."""
import asyncio
import json
import platform
import re
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import psutil

from src.config import settings
from src.domain.models.job import CommandLog, CommandStatus
from src.domain.models.template import EncoderType, EncodingTemplate, TemplateSideConfig, TemplateType
from src.domain.services.bd_rate import bd_rate as _bd_rate, bd_metrics as _bd_metrics
from src.application.bitstream_analyzer import build_bitstream_report
from src.infrastructure.persistence import job_repository


@dataclass
class SourceInfo:
    """Source video information."""
    path: Path
    is_yuv: bool
    width: int
    height: int
    fps: float
    pix_fmt: str = "yuv420p"


@dataclass
class PerformanceData:
    """Encoding performance data."""
    encoding_fps: Optional[float] = None
    avg_frame_time_ms: Optional[float] = None
    total_encoding_time_s: Optional[float] = None
    total_frames: Optional[int] = None
    cpu_avg_percent: Optional[float] = None
    cpu_max_percent: Optional[float] = None
    cpu_samples: List[float] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        result: Dict[str, Any] = {}
        if self.encoding_fps is not None:
            result["encoding_fps"] = round(self.encoding_fps, 2)
        if self.avg_frame_time_ms is not None:
            result["avg_frame_time_ms"] = round(self.avg_frame_time_ms, 2)
        if self.total_encoding_time_s is not None:
            result["total_encoding_time_s"] = round(self.total_encoding_time_s, 2)
        if self.total_frames is not None:
            result["total_frames"] = self.total_frames
        if self.cpu_avg_percent is not None:
            result["cpu_avg_percent"] = round(self.cpu_avg_percent, 2)
        if self.cpu_max_percent is not None:
            result["cpu_max_percent"] = round(self.cpu_max_percent, 2)
        return result


def _now():
    return datetime.now().astimezone()


def _fingerprint(config: TemplateSideConfig) -> str:
    """Generate fingerprint for config change detection."""
    import hashlib
    data = f"{config.encoder_type}:{config.encoder_params}:{config.rate_control}:{sorted(config.bitrate_points)}"
    return hashlib.md5(data.encode()).hexdigest()[:8]


async def _collect_sources(source_dir: str) -> List[SourceInfo]:
    """Collect source video information from directory."""
    from src.infrastructure.ffmpeg.prober import FFProber
    
    prober = FFProber(settings.get_ffprobe_bin())
    anchor = Path(source_dir)
    if not anchor.is_dir():
        raise ValueError(f"Source directory not found: {source_dir}")
    
    files = sorted([p for p in anchor.iterdir() if p.is_file()])
    if not files:
        raise ValueError(f"Source directory is empty: {source_dir}")

    results: List[SourceInfo] = []
    for p in files:
        if p.suffix.lower() == ".yuv":
            # Parse YUV filename: name_WxH_FPS.yuv
            m = re.search(r"_([0-9]+)x([0-9]+)_([0-9]+(?:\.[0-9]+)?)$", p.stem)
            if not m:
                raise ValueError(f"YUV filename format invalid: {p.name}")
            w, h, fps = int(m.group(1)), int(m.group(2)), float(m.group(3))
            results.append(SourceInfo(path=p, is_yuv=True, width=w, height=h, fps=fps))
        else:
            info = await prober.get_video_info(p)
            w, h, fps = info.get("width"), info.get("height"), info.get("fps")
            if not (w and h and fps):
                raise ValueError(f"Cannot parse resolution/fps: {p}")
            results.append(SourceInfo(path=p, is_yuv=False, width=int(w), height=int(h), fps=float(fps)))
    return results


class TemplateExecutor:
    """Template execution service."""

    async def execute(self, template: EncodingTemplate, job=None) -> Dict[str, Any]:
        """Execute template (comparison or metrics analysis)."""
        if template.metadata.template_type == TemplateType.METRICS_ANALYSIS:
            return await self._execute_metrics_analysis(template, job)
        return await self._execute_comparison(template, job)

    async def _execute_comparison(self, template: EncodingTemplate, job=None) -> Dict[str, Any]:
        """Execute comparison template (Anchor vs Test)."""
        # Validate rate control consistency
        if template.metadata.anchor.rate_control != template.metadata.test.rate_control:
            raise ValueError("Anchor and Test rate control mismatch")
        if sorted(template.metadata.anchor.bitrate_points or []) != sorted(template.metadata.test.bitrate_points or []):
            raise ValueError("Anchor and Test bitrate points mismatch")

        # Collect sources
        anchor_sources = await _collect_sources(template.metadata.anchor.source_dir)
        test_sources = await _collect_sources(template.metadata.test.source_dir)
        
        anchor_map = {p.path.stem: p for p in anchor_sources}
        test_map = {p.path.stem: p for p in test_sources}
        
        if set(anchor_map.keys()) != set(test_map.keys()):
            raise ValueError("Source files mismatch between Anchor and Test")
        
        ordered_sources = [anchor_map[k] for k in sorted(anchor_map.keys())]

        # Encode sides
        anchor_outputs, anchor_perfs = await self._encode_side(template.metadata.anchor, ordered_sources, job)
        test_outputs, test_perfs = await self._encode_side(
            template.metadata.test, 
            [test_map[s.path.stem] for s in ordered_sources], 
            job
        )

        # Calculate metrics
        analysis_root = Path(job.job_dir) / "analysis" if job else Path(template.template_dir) / "analysis"
        analysis_root.mkdir(parents=True, exist_ok=True)

        report_entries = []
        bd_metrics_list = []

        for src in ordered_sources:
            key = src.path.stem
            anchor_paths = anchor_outputs.get(key, [])
            test_paths = test_outputs.get(key, [])

            if not anchor_paths or not test_paths:
                raise ValueError(f"Missing bitstream: {src.path.name}")

            analysis_dir = analysis_root / src.path.stem
            
            anchor_report, anchor_summary = await build_bitstream_report(
                reference_path=src.path,
                encoded_paths=anchor_paths,
                analysis_dir=analysis_dir / "anchor",
                raw_width=src.width if src.is_yuv else None,
                raw_height=src.height if src.is_yuv else None,
                raw_fps=src.fps if src.is_yuv else None,
                raw_pix_fmt=src.pix_fmt,
            )
            test_report, test_summary = await build_bitstream_report(
                reference_path=src.path,
                encoded_paths=test_paths,
                analysis_dir=analysis_dir / "test",
                raw_width=src.width if src.is_yuv else None,
                raw_height=src.height if src.is_yuv else None,
                raw_fps=src.fps if src.is_yuv else None,
                raw_pix_fmt=src.pix_fmt,
            )

            # Calculate BD metrics
            bd_metrics_list.append(self._calculate_bd_metrics(src, anchor_report, test_report))
            report_entries.append({"source": src.path.name, "anchor": anchor_summary, "test": test_summary})

        result = {
            "kind": "template_metrics",
            "template_id": template.template_id,
            "template_name": template.metadata.name,
            "entries": report_entries,
            "bd_metrics": bd_metrics_list,
        }

        # Save report
        report_dir = Path(job.job_dir) / "metrics_analysis" if job else template.template_dir / "metrics_analysis"
        report_dir.mkdir(parents=True, exist_ok=True)
        report_path = report_dir / "report_data.json"
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, separators=(",", ":"))
        
        if job:
            result["report_data_file"] = str(report_path.relative_to(job.job_dir))

        return result

    async def _execute_metrics_analysis(self, template: EncodingTemplate, job=None) -> Dict[str, Any]:
        """Execute single-side metrics analysis."""
        config = template.metadata.anchor
        sources = await _collect_sources(config.source_dir)
        ordered_sources = sorted(sources, key=lambda s: s.path.name)

        encoded_outputs, _ = await self._encode_side(config, ordered_sources, job)

        analysis_root = Path(job.job_dir) / "metrics_analysis" if job else Path(template.template_dir) / "metrics_analysis"
        analysis_root.mkdir(parents=True, exist_ok=True)

        entries: List[Dict[str, Any]] = []
        for src in ordered_sources:
            paths = encoded_outputs.get(src.path.stem, [])
            if not paths:
                raise ValueError(f"Missing bitstream: {src.path.name}")
            
            report, _ = await build_bitstream_report(
                reference_path=src.path,
                encoded_paths=paths,
                analysis_dir=analysis_root / src.path.stem,
                raw_width=src.width if src.is_yuv else None,
                raw_height=src.height if src.is_yuv else None,
                raw_fps=src.fps if src.is_yuv else None,
                raw_pix_fmt=src.pix_fmt,
            )
            entries.append({"source": src.path.name, "encoded": report.get("encoded") or []})

        result = {
            "kind": "metrics_analysis_single",
            "template_id": template.template_id,
            "template_name": template.metadata.name,
            "entries": entries,
        }

        data_path = analysis_root / "analyse_data.json"
        with open(data_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        if job:
            result["data_file"] = str(data_path.relative_to(job.job_dir))

        return result

    async def _encode_side(
        self,
        side: TemplateSideConfig,
        sources: List[SourceInfo],
        job=None,
    ) -> Tuple[Dict[str, List[Path]], Dict[str, List[PerformanceData]]]:
        """Encode one side (Anchor or Test)."""
        outputs: Dict[str, List[Path]] = {}
        perf_data: Dict[str, List[PerformanceData]] = {}
        side_dir = Path(side.bitstream_dir)
        side_dir.mkdir(parents=True, exist_ok=True)

        for src in sources:
            file_outputs: List[Path] = []
            file_perfs: List[PerformanceData] = []
            
            for val in side.bitrate_points or []:
                rc = (side.rate_control.value if side.rate_control else "rc").lower()
                val_str = str(val).rstrip("0").rstrip(".") if isinstance(val, float) else str(val)
                stem = f"{src.path.stem}_{rc}_{val_str}"
                
                if side.skip_encode:
                    matches = list(side_dir.glob(f"{stem}.*"))
                    if matches:
                        file_outputs.append(matches[0])
                        file_perfs.append(PerformanceData())
                        continue
                    raise FileNotFoundError(f"Missing bitstream: {stem}")

                ext = self._get_output_extension(side.encoder_type, src)
                out_path = side_dir / f"{stem}{ext}"
                
                if out_path.exists():
                    file_outputs.append(out_path)
                    file_perfs.append(PerformanceData())
                    continue

                cmd = self._build_encode_cmd(side, val, src, out_path)
                perf = await self._run_encode_with_perf(cmd, side.encoder_type)
                file_outputs.append(out_path)
                file_perfs.append(perf)

            outputs[src.path.stem] = file_outputs
            perf_data[src.path.stem] = file_perfs

        return outputs, perf_data

    def _get_output_extension(self, enc: EncoderType, src: SourceInfo) -> str:
        """Get output file extension based on encoder type."""
        if enc == EncoderType.X264:
            return ".h264"
        if enc == EncoderType.X265:
            return ".h265"
        if enc == EncoderType.VVENC:
            return ".h266"
        return ".h264"

    def _build_encode_cmd(self, side: TemplateSideConfig, val: float, src: SourceInfo, output: Path) -> List[str]:
        """Build encoding command."""
        import shlex
        ffmpeg_path = settings.get_ffmpeg_bin()
        val_str = str(val)
        
        cmd = [ffmpeg_path, "-y"]
        if src.is_yuv:
            cmd += ["-f", "rawvideo", "-pix_fmt", src.pix_fmt, "-s:v", f"{src.width}x{src.height}", "-r", str(src.fps)]
        cmd += ["-i", str(src.path)]
        
        # Add encoder params (strip rate control tokens)
        tokens = shlex.split(side.encoder_params or "")
        skip_next = False
        for tok in tokens:
            if skip_next:
                skip_next = False
                continue
            if tok in {"-crf", "-b:v", "--crf", "--bitrate"}:
                skip_next = True
                continue
            cmd.append(tok)
        
        # Add rate control
        rc = side.rate_control.value if side.rate_control else "crf"
        if rc == "crf":
            cmd += ["-crf", val_str]
        else:
            cmd += ["-b:v", f"{val_str}k"]
        
        cmd.append(str(output))
        return cmd

    async def _run_encode_with_perf(self, cmd: List[str], encoder_type: EncoderType) -> PerformanceData:
        """Run encoding command and collect performance data."""
        perf = PerformanceData()
        
        proc = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        start_time = time.time()
        stdout, stderr = await proc.communicate()
        end_time = time.time()

        perf.total_encoding_time_s = end_time - start_time

        # Parse encoder output for FPS/frames
        stderr_str = stderr.decode(errors="ignore")
        frames, fps, _ = self._parse_encoder_output(stderr_str, encoder_type)
        
        if frames:
            perf.total_frames = frames
        if fps and fps > 0:
            perf.encoding_fps = fps
            perf.avg_frame_time_ms = 1000.0 / fps

        if proc.returncode != 0:
            raise RuntimeError(f"Encoding failed: {stderr_str}")

        return perf

    def _parse_encoder_output(self, stderr: str, encoder_type: EncoderType) -> Tuple[Optional[int], Optional[float], Optional[float]]:
        """Parse encoder output for frames, fps, total time."""
        frames, fps, total_time = None, None, None

        if encoder_type == EncoderType.FFMPEG:
            matches = re.findall(r"frame=\s*(\d+).*?fps=\s*([\d.]+)", stderr)
            if matches:
                frames = int(matches[-1][0])
                fps = float(matches[-1][1])
                if fps > 0:
                    total_time = frames / fps
        elif encoder_type == EncoderType.X264:
            m = re.search(r"encoded\s+(\d+)\s+frames,\s+([\d.]+)\s+fps", stderr)
            if m:
                frames, fps = int(m.group(1)), float(m.group(2))
                if fps > 0:
                    total_time = frames / fps
        elif encoder_type in {EncoderType.X265, EncoderType.VVENC}:
            m = re.search(r"encoded\s+(\d+)\s+frames\s+in\s+([\d.]+)s\s+\(([\d.]+)\s+fps\)", stderr)
            if m:
                frames, total_time, fps = int(m.group(1)), float(m.group(2)), float(m.group(3))

        return frames, fps, total_time

    def _calculate_bd_metrics(self, src: SourceInfo, anchor_report: Dict, test_report: Dict) -> Dict[str, Any]:
        """Calculate BD-Rate metrics between anchor and test."""
        def _extract_bitrate(item):
            return item.get("avg_bitrate_bps") or (item.get("bitrate") or {}).get("avg_bitrate_bps")

        def _extract_metric(item, key):
            metric = ((item.get("metrics") or {}).get(key) or {}).get("summary") or {}
            if not metric:
                metric = item.get(key) or {}
            return metric.get(f"{key}_avg") or metric.get(f"{key}_mean")

        def _collect(series, key):
            pts = []
            for item in series:
                bitrate = _extract_bitrate(item)
                val = _extract_metric(item, key)
                if bitrate and val:
                    pts.append((float(val), float(bitrate)))
            return pts

        def _pair_curves(key):
            pts_a = _collect(anchor_report.get("encoded", []), key)
            pts_b = _collect(test_report.get("encoded", []), key)
            if len(pts_a) < 4 or len(pts_b) < 4:
                return None
            m1, r1 = zip(*sorted(pts_a, key=lambda x: x[0]))
            m2, r2 = zip(*sorted(pts_b, key=lambda x: x[0]))
            return _bd_rate(list(r1), list(m1), list(r2), list(m2))

        return {
            "source": src.path.name,
            "bd_rate_psnr": _pair_curves("psnr"),
            "bd_rate_ssim": _pair_curves("ssim"),
            "bd_rate_vmaf": _pair_curves("vmaf"),
        }


# Global singleton
template_executor = TemplateExecutor()
