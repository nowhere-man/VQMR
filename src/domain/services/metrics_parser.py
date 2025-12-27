"""Metrics log parsing (pure parsing, no I/O except file read)."""
import csv
import json
from io import StringIO
from pathlib import Path
from typing import Any, Dict, List, Optional


def _safe_float(val: Any) -> Optional[float]:
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


def _mean(values: List[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _harmonic_mean(values: List[float]) -> float:
    positives = [v for v in values if v and v > 0]
    return len(positives) / sum(1.0 / v for v in positives) if positives else 0.0


def parse_psnr_log(log_path: Path) -> Dict[str, Any]:
    """Parse PSNR stats_file log."""
    frames_avg: List[float] = []
    frames_y: List[float] = []
    frames_u: List[float] = []
    frames_v: List[float] = []

    with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            if "psnr_avg" not in line:
                continue
            parts = line.strip().split()
            values: Dict[str, float] = {}
            for part in parts:
                if ":" not in part:
                    continue
                key, val = part.split(":", 1)
                if key.startswith("psnr_"):
                    parsed = _safe_float(val)
                    if parsed is not None:
                        values[key] = parsed
            if "psnr_avg" in values:
                frames_avg.append(values.get("psnr_avg", 0.0))
                frames_y.append(values.get("psnr_y", 0.0))
                frames_u.append(values.get("psnr_u", 0.0))
                frames_v.append(values.get("psnr_v", 0.0))

    if not frames_avg:
        raise ValueError(f"No PSNR data found in {log_path.name}")

    return {
        "summary": {
            "psnr_avg": _mean(frames_avg),
            "psnr_y": _mean(frames_y),
            "psnr_u": _mean(frames_u),
            "psnr_v": _mean(frames_v),
        },
        "frames": {
            "psnr_avg": frames_avg,
            "psnr_y": frames_y,
            "psnr_u": frames_u,
            "psnr_v": frames_v,
        },
    }


def parse_ssim_log(log_path: Path) -> Dict[str, Any]:
    """Parse SSIM stats_file log."""
    frames_all: List[float] = []
    frames_y: List[float] = []
    frames_u: List[float] = []
    frames_v: List[float] = []

    with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            if "All:" not in line:
                continue
            parts = line.strip().split()
            values: Dict[str, float] = {}
            for part in parts:
                if ":" not in part:
                    continue
                key, val = part.split(":", 1)
                key_norm = key.strip()
                if key_norm in ("Y", "U", "V", "All"):
                    parsed = _safe_float(val)
                    if parsed is not None:
                        values[key_norm] = parsed
            if "All" in values:
                frames_all.append(values.get("All", 0.0))
                frames_y.append(values.get("Y", 0.0))
                frames_u.append(values.get("U", 0.0))
                frames_v.append(values.get("V", 0.0))

    if not frames_all:
        raise ValueError(f"No SSIM data found in {log_path.name}")

    return {
        "summary": {
            "ssim_avg": _mean(frames_all),
            "ssim_y": _mean(frames_y),
            "ssim_u": _mean(frames_u),
            "ssim_v": _mean(frames_v),
        },
        "frames": {
            "ssim_avg": frames_all,
            "ssim_y": frames_y,
            "ssim_u": frames_u,
            "ssim_v": frames_v,
        },
    }


def parse_vmaf_log(log_path: Path) -> Dict[str, Any]:
    """Parse VMAF log file (JSON or CSV format)."""
    text = log_path.read_text(encoding="utf-8", errors="ignore")
    if not text.strip():
        raise ValueError(f"VMAF log is empty: {log_path.name}")

    if text.lstrip().startswith("{"):
        return _parse_vmaf_json(text)
    return _parse_vmaf_csv(text)


def _parse_vmaf_json(text: str) -> Dict[str, Any]:
    """Parse VMAF JSON format log."""
    data = json.loads(text)
    frames = data.get("frames", []) or []

    metric_keys = set()
    for frame in frames:
        metrics = frame.get("metrics", {}) or {}
        metric_keys.update(metrics.keys())

    metric_keys_sorted = sorted(metric_keys)
    frame_series: Dict[str, List[Optional[float]]] = {k: [] for k in metric_keys_sorted}

    for frame in frames:
        metrics = frame.get("metrics", {}) or {}
        for key in metric_keys_sorted:
            frame_series[key].append(_safe_float(metrics.get(key)))

    frame_series = {k: v for k, v in frame_series.items() if any(val is not None for val in v)}

    pooled = data.get("pooled_metrics", {}) or {}
    vmaf_pooled = pooled.get("vmaf", {}) or {}
    vmaf_neg_pooled = pooled.get("vmaf_neg", {}) or {}

    feature_summary: Dict[str, Dict[str, float]] = {}
    for key, stats in pooled.items():
        if not isinstance(stats, dict):
            continue
        entry: Dict[str, float] = {}
        mean_val = _safe_float(stats.get("mean"))
        harmonic_val = _safe_float(stats.get("harmonic_mean"))
        if mean_val is not None:
            entry["mean"] = mean_val
        if harmonic_val is not None:
            entry["harmonic_mean"] = harmonic_val
        if entry:
            feature_summary[key] = entry

    result: Dict[str, Any] = {
        "summary": {
            "vmaf_mean": _safe_float(vmaf_pooled.get("mean")) if vmaf_pooled else None,
            "vmaf_harmonic_mean": _safe_float(vmaf_pooled.get("harmonic_mean")) if vmaf_pooled else None,
            "vmaf_neg_mean": _safe_float(vmaf_neg_pooled.get("mean")) if vmaf_neg_pooled else None,
        },
        "frames": frame_series,
    }

    if feature_summary:
        result["feature_summary"] = feature_summary

    return result


def _parse_vmaf_csv(text: str) -> Dict[str, Any]:
    """Parse VMAF CSV format log."""
    reader = csv.DictReader(StringIO(text))
    fieldnames = reader.fieldnames or []
    metric_keys = [fn for fn in fieldnames if fn and fn.lower() not in {"frame", "index", "frame_num"}]

    frame_series: Dict[str, List[Optional[float]]] = {k: [] for k in metric_keys}
    for row in reader:
        for key in metric_keys:
            frame_series[key].append(_safe_float(row.get(key)))

    frame_series = {k: v for k, v in frame_series.items() if any(val is not None for val in v)}

    vmaf_vals = [v for v in frame_series.get("vmaf", []) if v is not None]
    vmaf_neg_vals = [v for v in frame_series.get("vmaf_neg", []) if v is not None]

    feature_summary: Dict[str, Dict[str, float]] = {}
    for key, vals in frame_series.items():
        nums = [v for v in vals if isinstance(v, (int, float))]
        if not nums:
            continue
        entry: Dict[str, float] = {"mean": _mean(nums)}
        harmonic = _harmonic_mean(nums)
        if harmonic:
            entry["harmonic_mean"] = harmonic
        feature_summary[key] = entry

    result: Dict[str, Any] = {
        "summary": {
            "vmaf_mean": _mean(vmaf_vals) if vmaf_vals else None,
            "vmaf_harmonic_mean": _harmonic_mean(vmaf_vals) if vmaf_vals else None,
            "vmaf_neg_mean": _mean(vmaf_neg_vals) if vmaf_neg_vals else None,
        },
        "frames": frame_series,
    }

    if feature_summary:
        result["feature_summary"] = feature_summary

    return result


def parse_psnr_summary(log_path: Path) -> Dict[str, float]:
    """Parse PSNR log, return summary only."""
    return parse_psnr_log(log_path)["summary"]


def parse_ssim_summary(log_path: Path) -> Dict[str, float]:
    """Parse SSIM log, return summary only."""
    return parse_ssim_log(log_path)["summary"]


def parse_vmaf_summary(log_path: Path) -> Dict[str, float]:
    """Parse VMAF log, return summary only."""
    summary = parse_vmaf_log(log_path)["summary"]
    return {k: v if v is not None else 0.0 for k, v in summary.items()}
