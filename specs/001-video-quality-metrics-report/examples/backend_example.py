"""
FastAPI 后端示例：Chart.js 数据传递
适用于 VQMR 项目的质量指标报告生成
"""

from fastapi import FastAPI, Request, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import json
import os

app = FastAPI(title="VQMR Chart.js 示例")

# 配置模板目录（实际项目中应使用相对路径）
CURRENT_DIR = Path(__file__).parent
templates = Jinja2Templates(directory=str(CURRENT_DIR))

# 挂载静态文件（可选，用于托管 JS/CSS）
# app.mount("/static", StaticFiles(directory="frontend/static"), name="static")


@app.get("/")
async def index():
    """首页：跳转到示例报告"""
    return {"message": "访问 /jobs/example_job_001/report 查看示例报告"}


@app.get("/jobs/{job_id}/report")
async def get_report(request: Request, job_id: str):
    """
    渲染质量指标报告页面

    Args:
        request: FastAPI Request 对象
        job_id: 任务 ID

    Returns:
        TemplateResponse: 渲染后的 HTML 页面
    """

    # 加载指标数据
    metrics_file = CURRENT_DIR / "sample_metrics.json"

    if not metrics_file.exists():
        raise HTTPException(status_code=404, detail="Metrics file not found")

    with open(metrics_file) as f:
        metrics = json.load(f)

    # 预处理数据（抽取、格式化）
    chart_data = prepare_chart_data(metrics)

    # 渲染模板
    return templates.TemplateResponse(
        "report_template.html",
        {
            "request": request,
            "job_id": job_id,
            "video_name": metrics.get("video_name"),
            "encoder": metrics.get("encoder"),
            "bitrate_kbps": metrics.get("bitrate_kbps"),
            "metrics_summary": metrics.get("summary"),
            "chart_data_json": json.dumps(chart_data),  # 序列化为 JSON 字符串
        }
    )


@app.get("/jobs/{job_id}/metrics.json")
async def get_metrics_json(job_id: str):
    """
    返回原始 JSON 数据（供 AJAX 调用）

    Args:
        job_id: 任务 ID

    Returns:
        JSONResponse: 原始指标数据
    """
    metrics_file = CURRENT_DIR / "sample_metrics.json"

    if not metrics_file.exists():
        raise HTTPException(status_code=404, detail="Metrics not found")

    with open(metrics_file) as f:
        data = json.load(f)

    return JSONResponse(content=data)


def prepare_chart_data(metrics: dict) -> dict:
    """
    预处理数据为 Chart.js 所需格式

    Args:
        metrics: 原始指标数据

    Returns:
        dict: 预处理后的图表数据
    """
    frames = metrics.get("frames", [])

    # 数据抽取（如果帧数超过 1000）
    if len(frames) > 1000:
        # 简单抽取：每 N 帧取一个
        step = len(frames) // 500
        frames = frames[::step]

    # 提取数据数组（减少前端计算）
    return {
        "labels": [f["frame_number"] for f in frames],
        "vmaf": [f["vmaf"] for f in frames],
        "psnr_y": [f["psnr_y"] for f in frames],
        "psnr_u": [f.get("psnr_u") for f in frames],
        "psnr_v": [f.get("psnr_v") for f in frames],
        "ssim": [f["ssim"] for f in frames],
        "encoding_time_ms": [f.get("encoding_time_ms") for f in frames]
    }


# 运行示例（开发环境）
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend_example:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
