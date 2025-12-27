"""BD-rate and BD-metrics helpers shared by Streamlit pages."""

from __future__ import annotations

from typing import Dict, List, Tuple

import pandas as pd

from src.utils.bd_rate import bd_rate, bd_metrics


def build_bd_rows(df: pd.DataFrame) -> Tuple[List[Dict[str, float]], List[Dict[str, float]]]:
    """Compute BD-Rate and BD-Metrics rows grouped by video."""
    bd_rate_rows: List[Dict[str, float]] = []
    bd_metric_rows: List[Dict[str, float]] = []
    grouped = df.groupby("Video")
    for video, g in grouped:
        anchor = g[g["Side"] == "Anchor"]
        test = g[g["Side"] == "Test"]
        if anchor.empty or test.empty:
            continue
        merge = anchor.merge(test, on=["Video", "RC", "Point"], suffixes=("_anchor", "_test"))
        if merge.empty:
            continue

        def _collect(col_anchor: str, col_test: str) -> Tuple[List[float], List[float], List[float], List[float]]:
            merged = merge.dropna(subset=[col_anchor, col_test, "Bitrate_kbps_anchor", "Bitrate_kbps_test"])
            if merged.empty:
                return [], [], [], []
            return (
                merged["Bitrate_kbps_anchor"].tolist(),
                merged[col_anchor].tolist(),
                merged["Bitrate_kbps_test"].tolist(),
                merged[col_test].tolist(),
            )

        anchor_rates, anchor_psnr, test_rates, test_psnr = _collect("PSNR_anchor", "PSNR_test")
        _, anchor_ssim, _, test_ssim = _collect("SSIM_anchor", "SSIM_test")
        _, anchor_vmaf, _, test_vmaf = _collect("VMAF_anchor", "VMAF_test")
        _, anchor_vn, _, test_vn = _collect("VMAF-NEG_anchor", "VMAF-NEG_test")

        bd_rate_rows.append(
            {
                "Video": video,
                "BD-Rate PSNR (%)": bd_rate(anchor_rates, anchor_psnr, test_rates, test_psnr),
                "BD-Rate SSIM (%)": bd_rate(anchor_rates, anchor_ssim, test_rates, test_ssim),
                "BD-Rate VMAF (%)": bd_rate(anchor_rates, anchor_vmaf, test_rates, test_vmaf),
                "BD-Rate VMAF-NEG (%)": bd_rate(anchor_rates, anchor_vn, test_rates, test_vn),
            }
        )
        bd_metric_rows.append(
            {
                "Video": video,
                "BD PSNR": bd_metrics(anchor_rates, anchor_psnr, test_rates, test_psnr),
                "BD SSIM": bd_metrics(anchor_rates, anchor_ssim, test_rates, test_ssim),
                "BD VMAF": bd_metrics(anchor_rates, anchor_vmaf, test_rates, test_vmaf),
                "BD VMAF-NEG": bd_metrics(anchor_rates, anchor_vn, test_rates, test_vn),
            }
        )
    return bd_rate_rows, bd_metric_rows
