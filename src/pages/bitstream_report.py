"""
码流分析报告页面（Streamlit）

通过 `?job_id=<job_id>` 打开对应任务的报告。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st


# 添加项目根目录到Python路径
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

from src.config import settings


def _jobs_root_dir() -> Path:
    root = settings.jobs_root_dir
    if root.is_absolute():
        return root
    return (project_root / root).resolve()


def _get_job_id() -> Optional[str]:
    job_id = st.query_params.get("job_id")
    if job_id:
        if isinstance(job_id, list):
            job_id = job_id[0] if job_id else None
        return str(job_id) if job_id else None
    return st.session_state.get("bitstream_job_id")


def _load_report(job_id: str) -> Dict[str, Any]:
    report_path = _jobs_root_dir() / job_id / "bitstream_analysis" / "report_data.json"
    if not report_path.exists():
        raise FileNotFoundError(f"未找到报告数据文件: {report_path}")
    with open(report_path, "r", encoding="utf-8") as f:
        return json.load(f)


def _plot_frame_lines(
    encoded: List[Dict[str, Any]],
    y_series_getter,
    title: str,
    yaxis_title: str,
) -> None:
    fig = go.Figure()
    for item in encoded:
        label = item.get("label", "Encoded")
        values = y_series_getter(item)
        fig.add_trace(go.Scatter(x=list(range(len(values))), y=values, mode="lines", name=label))
    fig.update_layout(
        title=title,
        xaxis_title="Frame",
        yaxis_title=yaxis_title,
        hovermode="x unified",
    )
    st.plotly_chart(fig, use_container_width=True)


st.set_page_config(page_title="码流分析报告 - VQMR", page_icon="📊", layout="wide")
st.title("📊 码流分析报告")

job_id = _get_job_id()
if not job_id:
    st.warning("缺少 job_id，请从任务详情页点击“打开 Streamlit 报告”。")
    st.stop()

# 保持 session_state，方便从首页跳转
st.session_state["bitstream_job_id"] = job_id

try:
    report = _load_report(job_id)
except Exception as exc:
    st.error(str(exc))
    st.stop()

if report.get("kind") != "bitstream_analysis":
    st.error("该任务不是码流分析报告或报告数据格式不匹配。")
    st.stop()

ref = report.get("reference", {}) or {}
encoded_items = report.get("encoded", []) or []

st.caption(
    f"Job: {job_id} | Ref: {ref.get('label')} | "
    f"{ref.get('width')}x{ref.get('height')} @ {ref.get('fps')} fps | {ref.get('frames')} frames"
)
st.info("说明：所有打分输入统一转换为 yuv420p；若 Encoded 分辨率不一致会先对齐到 Ref；若帧数/时长不一致任务会直接失败。")

if not encoded_items:
    st.warning("报告中未包含任何 Encoded 数据。")
    st.stop()


# ========== 1) Metrics ==========
st.header("1) Metrics")

rows = []
for item in encoded_items:
    metrics = item.get("metrics", {}) or {}
    psnr = (metrics.get("psnr", {}) or {}).get("summary", {}) or {}
    ssim = (metrics.get("ssim", {}) or {}).get("summary", {}) or {}
    vmaf = (metrics.get("vmaf", {}) or {}).get("summary", {}) or {}
    bitrate = item.get("bitrate", {}) or {}

    rows.append(
        {
            "Encoded": item.get("label"),
            "PSNR_avg": psnr.get("psnr_avg"),
            "PSNR_y": psnr.get("psnr_y"),
            "PSNR_u": psnr.get("psnr_u"),
            "PSNR_v": psnr.get("psnr_v"),
            "SSIM_avg": ssim.get("ssim_avg"),
            "SSIM_y": ssim.get("ssim_y"),
            "SSIM_u": ssim.get("ssim_u"),
            "SSIM_v": ssim.get("ssim_v"),
            "VMAF": vmaf.get("vmaf_mean"),
            "VMAF-neg": vmaf.get("vmaf_neg_mean"),
            "Avg Bitrate (kbps)": (bitrate.get("avg_bitrate_bps") or 0) / 1000,
        }
    )

df_metrics = pd.DataFrame(rows)
st.dataframe(df_metrics, use_container_width=True, hide_index=True)

st.subheader("逐帧折线图")

tab_psnr, tab_ssim, tab_vmaf = st.tabs(["PSNR", "SSIM", "VMAF / VMAF-neg"])

with tab_psnr:
    comp = st.selectbox("分量", ["avg", "y", "u", "v"], key="psnr_comp")
    key_map = {"avg": "psnr_avg", "y": "psnr_y", "u": "psnr_u", "v": "psnr_v"}
    metric_key = key_map[comp]
    _plot_frame_lines(
        encoded_items,
        lambda item: (((item.get("metrics") or {}).get("psnr") or {}).get("frames") or {}).get(metric_key, []),
        f"PSNR ({metric_key}) - 每帧",
        "PSNR (dB)",
    )

with tab_ssim:
    comp = st.selectbox("分量", ["avg", "y", "u", "v"], key="ssim_comp")
    key_map = {"avg": "ssim_avg", "y": "ssim_y", "u": "ssim_u", "v": "ssim_v"}
    metric_key = key_map[comp]
    _plot_frame_lines(
        encoded_items,
        lambda item: (((item.get("metrics") or {}).get("ssim") or {}).get("frames") or {}).get(metric_key, []),
        f"SSIM ({metric_key}) - 每帧",
        "SSIM",
    )

with tab_vmaf:
    _plot_frame_lines(
        encoded_items,
        lambda item: (((item.get("metrics") or {}).get("vmaf") or {}).get("frames") or {}).get("vmaf", []),
        "VMAF - 每帧",
        "VMAF",
    )
    _plot_frame_lines(
        encoded_items,
        lambda item: (((item.get("metrics") or {}).get("vmaf") or {}).get("frames") or {}).get("vmaf_neg", []),
        "VMAF-neg - 每帧",
        "VMAF-neg",
    )


# ========== 2) Bitrate ==========
st.header("2) Bitrate")

bitrate_rows = []
for item in encoded_items:
    bitrate = item.get("bitrate", {}) or {}
    bitrate_rows.append(
        {
            "Encoded": item.get("label"),
            "Avg Bitrate (kbps)": (bitrate.get("avg_bitrate_bps") or 0) / 1000,
        }
    )

st.dataframe(pd.DataFrame(bitrate_rows), use_container_width=True, hide_index=True)

st.subheader("按时间间隔聚合的码率图")

chart_type = st.selectbox("图形类型", ["折线图", "柱状图"], key="br_chart_type")
bin_seconds = st.slider("聚合间隔 (秒)", min_value=0.1, max_value=5.0, value=1.0, step=0.1, key="br_bin")

fig = go.Figure()
for item in encoded_items:
    bitrate = item.get("bitrate", {}) or {}
    ts = bitrate.get("frame_timestamps", []) or []
    sizes = bitrate.get("frame_sizes", []) or []

    bins: Dict[int, float] = {}
    for t, s in zip(ts, sizes):
        try:
            idx = int(float(t) / bin_seconds)
        except (TypeError, ValueError):
            continue
        bins[idx] = bins.get(idx, 0.0) + float(s) * 8.0

    xs = sorted(bins.keys())
    x_times = [i * bin_seconds for i in xs]
    y_kbps = [(bins[i] / bin_seconds) / 1000.0 for i in xs]

    if chart_type == "柱状图":
        fig.add_trace(go.Bar(x=x_times, y=y_kbps, name=item.get("label")))
    else:
        fig.add_trace(go.Scatter(x=x_times, y=y_kbps, mode="lines+markers", name=item.get("label")))

fig.update_layout(
    title=f"码率 (聚合间隔 {bin_seconds}s)",
    xaxis_title="Time (s)",
    yaxis_title="Bitrate (kbps)",
    hovermode="x unified",
    barmode="group",
)
st.plotly_chart(fig, use_container_width=True)

st.subheader("帧结构：帧类型与帧大小（按 Encoded 分行）")
st.caption("颜色提示：I/IDR=蓝, P=绿, B=橙, RAW/UNK=灰。")

color_map = {
    "I": "#2563eb",
    "IDR": "#2563eb",
    "P": "#16a34a",
    "B": "#f97316",
    "RAW": "#6b7280",
    "UNK": "#6b7280",
}

rows_count = len(encoded_items)
subplot_titles = [str(item.get("label")) for item in encoded_items]
fig_frames = make_subplots(
    rows=rows_count,
    cols=1,
    shared_xaxes=True,
    vertical_spacing=0.03,
    subplot_titles=subplot_titles,
)

for r, item in enumerate(encoded_items, start=1):
    bitrate = item.get("bitrate", {}) or {}
    types = bitrate.get("frame_types", []) or []
    sizes = bitrate.get("frame_sizes", []) or []
    colors = [color_map.get(str(t), "#6b7280") for t in types]
    hover = [
        f"Frame {i}<br>Type: {types[i] if i < len(types) else 'UNK'}<br>Size: {sizes[i]} bytes"
        for i in range(len(sizes))
    ]
    fig_frames.add_trace(
        go.Bar(
            x=list(range(len(sizes))),
            y=sizes,
            marker_color=colors,
            hovertext=hover,
            hoverinfo="text",
            showlegend=False,
        ),
        row=r,
        col=1,
    )
    fig_frames.update_yaxes(title_text="Bytes", row=r, col=1)

fig_frames.update_layout(
    height=max(320, 220 * rows_count),
    xaxis_title="Frame",
)

st.plotly_chart(fig_frames, use_container_width=True)
