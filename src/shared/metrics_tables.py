"""Shared helpers to build metrics comparison tables."""

from __future__ import annotations

from typing import Any, Dict, List

import pandas as pd

from src.utils.streamlit_helpers import parse_rate_point

MetricsRow = Dict[str, Any]


def build_metrics_rows(entries: List[Dict[str, Any]]) -> pd.DataFrame:
    """Flatten metrics entries into a DataFrame with common columns."""
    rows: List[MetricsRow] = []
    for entry in entries:
        video = entry.get("source")
        for side_key, side_name in (("anchor", "Anchor"), ("test", "Test")):
            side = (entry.get(side_key) or {})
            for item in side.get("encoded", []) or []:
                rc, point = parse_rate_point(item.get("label", ""))
                psnr_avg = (item.get("psnr") or {}).get("psnr_avg")
                ssim_avg = (item.get("ssim") or {}).get("ssim_avg")
                vmaf_mean = (item.get("vmaf") or {}).get("vmaf_mean")
                vmaf_neg_mean = (item.get("vmaf") or {}).get("vmaf_neg_mean")
                rows.append(
                    {
                        "Video": video,
                        "Side": side_name,
                        "RC": rc,
                        "Point": point,
                        "Bitrate_kbps": (item.get("avg_bitrate_bps") or 0) / 1000,
                        "PSNR": psnr_avg,
                        "SSIM": ssim_avg,
                        "VMAF": vmaf_mean,
                        "VMAF-NEG": vmaf_neg_mean,
                    }
                )
    return pd.DataFrame(rows)
