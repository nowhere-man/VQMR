# FastAPI + Jinja2 服务端渲染（SSR）Web 应用架构研究

**研究日期**: 2025-10-25
**应用场景**: VQMR 视频质量指标报告系统
**技术栈**: FastAPI + Jinja2 + Tailwind CSS + Chart.js

---

## 目录

1. [项目结构](#1-项目结构)
2. [路由设计](#2-路由设计)
3. [模板引擎集成](#3-模板引擎集成)
4. [任务管理](#4-任务管理)
5. [错误处理](#5-错误处理)
6. [架构图](#6-架构图)
7. [完整代码示例](#7-完整代码示例)
8. [最佳实践清单](#8-最佳实践清单)
9. [与 Django/Flask 对比](#9-与-djangoflask-对比)

---

## 1. 项目结构

### 1.1 推荐目录布局

```text
vqmr/                           # 项目根目录
├── backend/                    # 后端应用
│   ├── src/
│   │   ├── __init__.py
│   │   ├── main.py             # FastAPI 应用入口
│   │   ├── config.py           # 配置管理（从 .env 加载）
│   │   │
│   │   ├── models/             # 数据模型（Pydantic）
│   │   │   ├── __init__.py
│   │   │   ├── task.py         # EncodingTask, TaskStatus
│   │   │   ├── video.py        # VideoFile, VideoMetadata
│   │   │   └── metrics.py      # MetricsResult, PSNRData, VMAFData
│   │   │
│   │   ├── services/           # 业务逻辑层
│   │   │   ├── __init__.py
│   │   │   ├── ffmpeg.py       # FFmpegService（编码、指标计算）
│   │   │   ├── metrics.py      # MetricsService（解析日志、生成 JSON/CSV）
│   │   │   └── task.py         # TaskService（任务生命周期管理）
│   │   │
│   │   ├── api/                # API 路由
│   │   │   ├── __init__.py
│   │   │   ├── pages.py        # 页面路由（GET /、GET /jobs/{id}）
│   │   │   ├── jobs.py         # 任务 API（POST /jobs、GET /jobs/{id}/status）
│   │   │   ├── data.py         # 数据 API（GET /jobs/{id}/psnr.json）
│   │   │   └── health.py       # 健康检查（GET /health）
│   │   │
│   │   ├── templates/          # Jinja2 模板
│   │   │   ├── base.html       # 基础模板（包含 Tailwind/Chart.js CDN）
│   │   │   ├── upload.html     # 上传页面（继承 base.html）
│   │   │   ├── report.html     # 报告页面（继承 base.html）
│   │   │   └── error.html      # 错误页面（404/500）
│   │   │
│   │   └── utils/              # 工具函数
│   │       ├── __init__.py
│   │       ├── logger.py       # 结构化日志
│   │       └── validators.py   # 自定义验证器
│   │
│   └── tests/                  # 测试套件
│       ├── contract/           # API 契约测试
│       │   ├── test_pages.py
│       │   └── test_jobs_api.py
│       ├── integration/        # 端到端测试
│       │   └── test_user_flow.py
│       └── conftest.py         # pytest 配置
│
├── frontend/                   # 前端资源
│   └── static/
│       ├── css/
│       │   └── custom.css      # 补充样式（Tailwind 之外）
│       └── js/
│           ├── upload.js       # 上传页表单交互
│           └── report.js       # 报告页图表渲染
│
├── jobs/                       # 任务数据目录（由应用创建）
│   ├── {job_id_1}/
│   │   ├── input.mp4
│   │   ├── output.mp4
│   │   ├── psnr.log
│   │   ├── psnr.json
│   │   ├── psnr.csv
│   │   └── metadata.json       # 任务状态、参数、时间戳
│   └── {job_id_2}/
│       └── ...
│
├── docs/                       # 文档
│   ├── api.md
│   └── deployment.md
│
├── .env.example                # 环境变量模板
├── .env                        # 实际环境变量（不提交到 Git）
├── requirements.txt            # Python 依赖
├── pytest.ini                  # pytest 配置
├── Dockerfile                  # Docker 镜像
├── docker-compose.yml          # 一键启动
└── README.md
```

### 1.2 静态资源挂载策略

FastAPI 通过 `StaticFiles` 挂载静态资源：

```python
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

app = FastAPI()

# 挂载静态文件目录
app.mount("/static", StaticFiles(directory="frontend/static"), name="static")
```

**访问方式**:
- CSS: `<link href="/static/css/custom.css">`
- JS: `<script src="/static/js/upload.js"></script>`
- 图片: `<img src="/static/images/logo.png">`

**最佳实践**:
1. 使用绝对路径 `/static/...` 避免相对路径问题
2. 生产环境推荐用 Nginx 直接服务静态文件（性能更优）
3. 静态资源版本化：`/static/css/main.css?v=1.2.0`

---

## 2. 路由设计

### 2.1 完整路由表

| 方法 | 路径 | 类型 | 功能 | 返回 |
|------|------|------|------|------|
| GET | `/` | 页面 | 上传页面 | HTML (Jinja2) |
| POST | `/jobs` | API | 创建任务 | 302 重定向到 `/jobs/{id}` |
| GET | `/jobs/{id}` | 页面 | 任务详情/报告页 | HTML (Jinja2) |
| GET | `/jobs/{id}/status` | API | 查询任务状态 | JSON |
| GET | `/jobs/{id}/psnr.json` | API | 获取 PSNR 数据 | JSON |
| GET | `/jobs/{id}/psnr.csv` | API | 下载 CSV | CSV 文件 |
| GET | `/health` | API | 健康检查 | JSON |

### 2.2 路由实现示例

#### 2.2.1 页面路由 (`backend/src/api/pages.py`)

```python
from fastapi import APIRouter, Request, Depends
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from ..services.task import TaskService

router = APIRouter(tags=["Pages"])
templates = Jinja2Templates(directory="backend/src/templates")

@router.get("/", response_class=HTMLResponse)
async def upload_page(request: Request):
    """上传页面 - 显示表单"""
    return templates.TemplateResponse(
        "upload.html",
        {
            "request": request,
            "title": "视频质量指标报告 - 上传视频"
        }
    )

@router.get("/jobs/{job_id}", response_class=HTMLResponse)
async def report_page(
    request: Request,
    job_id: str,
    task_service: TaskService = Depends()
):
    """报告页面 - 显示任务状态和指标"""
    task = await task_service.get_task(job_id)

    return templates.TemplateResponse(
        "report.html",
        {
            "request": request,
            "title": f"任务报告 - {job_id}",
            "job_id": job_id,
            "task": task,  # 传递任务对象到模板
        }
    )
```

#### 2.2.2 任务 API (`backend/src/api/jobs.py`)

```python
from fastapi import APIRouter, Form, UploadFile, File, HTTPException, Depends
from fastapi.responses import RedirectResponse
from ..models.task import EncodingTask, TaskCreate
from ..services.task import TaskService
from typing import Optional
import uuid

router = APIRouter(prefix="/jobs", tags=["Jobs"])

@router.post("", status_code=303)
async def create_job(
    # 表单字段（python-multipart 自动解析）
    encoder_path: str = Form(..., description="编码器可执行文件路径"),
    bitrate: Optional[str] = Form(None, description="ABR 码率（如 2000k）"),
    crf: Optional[int] = Form(None, description="CRF 值（0-51）"),

    # 文件上传
    video_file: UploadFile = File(..., description="待编码视频文件"),
    reference_file: Optional[UploadFile] = File(None, description="参考视频（双文件模式）"),

    task_service: TaskService = Depends()
):
    """
    创建编码任务

    表单验证:
    - encoder_path 必须存在且可执行
    - bitrate 和 crf 二选一（不能同时为空）
    - video_file 必须是 .mp4/.flv 格式
    """

    # 1. 生成任务 ID
    job_id = str(uuid.uuid4())

    # 2. 验证表单数据
    if not bitrate and not crf:
        raise HTTPException(400, "bitrate 或 crf 必须提供一个")

    # 3. 创建任务对象
    task_data = TaskCreate(
        job_id=job_id,
        encoder_path=encoder_path,
        bitrate=bitrate,
        crf=crf,
        video_filename=video_file.filename
    )

    # 4. 保存上传文件并启动任务
    task = await task_service.create_task(
        task_data=task_data,
        video_file=video_file,
        reference_file=reference_file
    )

    # 5. 重定向到报告页（303 状态码确保浏览器用 GET 请求）
    return RedirectResponse(
        url=f"/jobs/{job_id}",
        status_code=303
    )

@router.get("/{job_id}/status")
async def get_job_status(
    job_id: str,
    task_service: TaskService = Depends()
):
    """获取任务状态（AJAX 轮询）"""
    task = await task_service.get_task(job_id)

    return {
        "job_id": job_id,
        "status": task.status,  # queued/processing/completed/failed
        "progress": task.progress,  # 0-100
        "error": task.error_message if task.status == "failed" else None
    }
```

#### 2.2.3 数据 API (`backend/src/api/data.py`)

```python
from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse, JSONResponse
from ..services.metrics import MetricsService

router = APIRouter(prefix="/jobs/{job_id}", tags=["Data"])

@router.get("/psnr.json")
async def get_psnr_data(
    job_id: str,
    metrics_service: MetricsService = Depends()
):
    """获取 PSNR 指标 JSON 数据（Chart.js 使用）"""
    data = await metrics_service.load_metrics(job_id, "psnr")

    return JSONResponse(content={
        "job_id": job_id,
        "metric": "psnr",
        "frames": data.frames,  # [{"frame": 1, "psnr_y": 42.5, ...}, ...]
        "average": data.average,
        "min": data.min,
        "max": data.max
    })

@router.get("/psnr.csv")
async def download_psnr_csv(job_id: str):
    """下载 PSNR CSV 文件"""
    file_path = f"jobs/{job_id}/psnr.csv"

    return FileResponse(
        path=file_path,
        filename=f"{job_id}_psnr.csv",
        media_type="text/csv"
    )
```

### 2.3 表单上传最佳实践

#### 关键点

1. **安装依赖**: `pip install python-multipart`
2. **表单字段**: 使用 `Form()` 声明
3. **文件上传**: 使用 `UploadFile` 类型（比 `bytes` 更高效）
4. **混合表单**: `Form()` 和 `File()` 可同时使用
5. **端点类型**: 使用 `def` 而非 `async def`（大文件 I/O 操作）

#### 文件保存示例

```python
from pathlib import Path
import shutil

async def save_uploaded_file(upload_file: UploadFile, destination: Path):
    """流式保存上传文件（避免内存溢出）"""
    destination.parent.mkdir(parents=True, exist_ok=True)

    with destination.open("wb") as buffer:
        shutil.copyfileobj(upload_file.file, buffer)
```

#### 文件验证

```python
from fastapi import HTTPException

ALLOWED_EXTENSIONS = {".mp4", ".flv", ".mov"}
MAX_FILE_SIZE = 500 * 1024 * 1024  # 500MB

def validate_video_file(file: UploadFile):
    """验证上传文件"""
    # 检查扩展名
    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            400,
            f"不支持的文件格式 {ext}，仅支持 {ALLOWED_EXTENSIONS}"
        )

    # 检查文件大小（需要流式读取）
    file.file.seek(0, 2)  # 移动到文件末尾
    size = file.file.tell()
    file.file.seek(0)  # 重置到开头

    if size > MAX_FILE_SIZE:
        raise HTTPException(400, f"文件超过最大限制 {MAX_FILE_SIZE / 1024 / 1024}MB")
```

---

## 3. 模板引擎集成

### 3.1 Jinja2 配置

```python
from fastapi.templating import Jinja2Templates
from pathlib import Path

# 模板目录配置
TEMPLATES_DIR = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# 自定义过滤器（可选）
def format_duration(seconds: float) -> str:
    """将秒转换为 mm:ss 格式"""
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{minutes:02d}:{secs:02d}"

templates.env.filters["duration"] = format_duration
```

### 3.2 模板继承结构

#### `base.html` - 基础模板

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}VQMR - 视频质量指标报告{% endblock %}</title>

    <!-- Tailwind CSS CDN -->
    <script src="https://cdn.tailwindcss.com"></script>

    <!-- Chart.js CDN -->
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>

    <!-- 自定义样式 -->
    <link rel="stylesheet" href="/static/css/custom.css">

    {% block extra_head %}{% endblock %}
</head>
<body class="bg-gray-50 min-h-screen">
    <!-- 导航栏 -->
    <nav class="bg-white shadow-sm border-b">
        <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div class="flex justify-between h-16 items-center">
                <h1 class="text-xl font-semibold text-gray-900">
                    VQMR - 视频质量指标报告
                </h1>
                <a href="/" class="text-blue-600 hover:text-blue-800">
                    返回首页
                </a>
            </div>
        </div>
    </nav>

    <!-- 主内容区 -->
    <main class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {% block content %}{% endblock %}
    </main>

    <!-- 页脚 -->
    <footer class="bg-white border-t mt-12">
        <div class="max-w-7xl mx-auto px-4 py-6 text-center text-gray-500 text-sm">
            VQMR v0.1.0 | Powered by FastAPI + Jinja2
        </div>
    </footer>

    {% block scripts %}{% endblock %}
</body>
</html>
```

#### `upload.html` - 上传页

```html
{% extends "base.html" %}

{% block title %}上传视频 - VQMR{% endblock %}

{% block content %}
<div class="max-w-2xl mx-auto">
    <h2 class="text-2xl font-bold text-gray-900 mb-6">创建编码任务</h2>

    <form action="/jobs" method="POST" enctype="multipart/form-data"
          class="bg-white shadow rounded-lg p-6 space-y-6">

        <!-- 编码器路径 -->
        <div>
            <label class="block text-sm font-medium text-gray-700 mb-2">
                编码器路径 *
            </label>
            <input type="text" name="encoder_path" required
                   placeholder="/usr/local/bin/ffmpeg"
                   class="w-full px-3 py-2 border border-gray-300 rounded-md">
        </div>

        <!-- 码控参数 -->
        <div class="grid grid-cols-2 gap-4">
            <div>
                <label class="block text-sm font-medium text-gray-700 mb-2">
                    ABR 码率（如 2000k）
                </label>
                <input type="text" name="bitrate" placeholder="2000k"
                       class="w-full px-3 py-2 border border-gray-300 rounded-md">
            </div>
            <div>
                <label class="block text-sm font-medium text-gray-700 mb-2">
                    CRF 值（0-51）
                </label>
                <input type="number" name="crf" min="0" max="51"
                       placeholder="23"
                       class="w-full px-3 py-2 border border-gray-300 rounded-md">
            </div>
        </div>
        <p class="text-sm text-gray-500">* ABR 和 CRF 二选一</p>

        <!-- 视频文件 -->
        <div>
            <label class="block text-sm font-medium text-gray-700 mb-2">
                待编码视频 *
            </label>
            <input type="file" name="video_file" accept=".mp4,.flv,.mov" required
                   class="w-full">
        </div>

        <!-- 参考视频（可选） -->
        <div>
            <label class="block text-sm font-medium text-gray-700 mb-2">
                参考视频（双文件模式）
            </label>
            <input type="file" name="reference_file" accept=".mp4,.flv,.mov"
                   class="w-full">
        </div>

        <!-- 提交按钮 -->
        <button type="submit"
                class="w-full bg-blue-600 text-white py-2 px-4 rounded-md
                       hover:bg-blue-700 transition">
            创建任务
        </button>
    </form>
</div>

<script src="/static/js/upload.js"></script>
{% endblock %}
```

#### `report.html` - 报告页

```html
{% extends "base.html" %}

{% block title %}任务报告 - {{ job_id }} - VQMR{% endblock %}

{% block content %}
<div class="space-y-6">
    <!-- 任务状态卡片 -->
    <div class="bg-white shadow rounded-lg p-6">
        <h2 class="text-xl font-bold mb-4">任务状态</h2>
        <div class="grid grid-cols-3 gap-4">
            <div>
                <p class="text-sm text-gray-500">任务 ID</p>
                <p class="font-mono text-sm">{{ job_id }}</p>
            </div>
            <div>
                <p class="text-sm text-gray-500">状态</p>
                <p class="font-semibold" id="task-status">
                    {% if task.status == 'completed' %}
                        <span class="text-green-600">已完成</span>
                    {% elif task.status == 'processing' %}
                        <span class="text-yellow-600">处理中</span>
                    {% elif task.status == 'failed' %}
                        <span class="text-red-600">失败</span>
                    {% else %}
                        <span class="text-gray-600">排队中</span>
                    {% endif %}
                </p>
            </div>
            <div>
                <p class="text-sm text-gray-500">进度</p>
                <div class="flex items-center space-x-2">
                    <div class="flex-1 bg-gray-200 rounded-full h-2">
                        <div class="bg-blue-600 h-2 rounded-full"
                             style="width: {{ task.progress }}%"></div>
                    </div>
                    <span class="text-sm font-medium">{{ task.progress }}%</span>
                </div>
            </div>
        </div>
    </div>

    <!-- PSNR 图表 -->
    {% if task.status == 'completed' %}
    <div class="bg-white shadow rounded-lg p-6">
        <h2 class="text-xl font-bold mb-4">PSNR 指标曲线</h2>
        <canvas id="psnr-chart"></canvas>
    </div>

    <!-- 下载区域 -->
    <div class="bg-white shadow rounded-lg p-6">
        <h2 class="text-xl font-bold mb-4">下载报告</h2>
        <div class="flex space-x-4">
            <a href="/jobs/{{ job_id }}/psnr.csv" download
               class="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700">
                下载 PSNR CSV
            </a>
            <a href="/jobs/{{ job_id }}/vmaf.csv" download
               class="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700">
                下载 VMAF CSV
            </a>
        </div>
    </div>
    {% endif %}
</div>
{% endblock %}

{% block scripts %}
<script>
// 将后端数据传递到前端
const jobId = "{{ job_id }}";
const taskStatus = "{{ task.status }}";

// 如果任务未完成，启动轮询
if (taskStatus !== 'completed' && taskStatus !== 'failed') {
    pollTaskStatus();
}

// 如果任务已完成，加载图表数据
if (taskStatus === 'completed') {
    loadPSNRChart();
}

// 轮询任务状态
function pollTaskStatus() {
    setInterval(async () => {
        const response = await fetch(`/jobs/${jobId}/status`);
        const data = await response.json();

        // 更新页面状态（省略 DOM 操作代码）
        if (data.status === 'completed') {
            location.reload();  // 重新加载页面显示报告
        }
    }, 2000);  // 每 2 秒查询一次
}

// 加载 PSNR 图表
async function loadPSNRChart() {
    const response = await fetch(`/jobs/${jobId}/psnr.json`);
    const data = await response.json();

    const ctx = document.getElementById('psnr-chart').getContext('2d');
    new Chart(ctx, {
        type: 'line',
        data: {
            labels: data.frames.map(f => f.frame),
            datasets: [{
                label: 'PSNR-Y (dB)',
                data: data.frames.map(f => f.psnr_y),
                borderColor: 'rgb(59, 130, 246)',
                backgroundColor: 'rgba(59, 130, 246, 0.1)',
            }]
        },
        options: {
            responsive: true,
            plugins: {
                title: {
                    display: true,
                    text: `PSNR 曲线 (平均: ${data.average.toFixed(2)} dB)`
                }
            }
        }
    });
}
</script>
{% endblock %}
```

### 3.3 传递数据到前端的策略

#### 方法 1: 内联 JSON（推荐用于简单数据）

```html
<script>
const taskData = {{ task | tojson }};  {# Jinja2 自动转义 #}
console.log(taskData.status);
</script>
```

#### 方法 2: AJAX 异步加载（推荐用于大数据）

```javascript
async function loadData() {
    const response = await fetch(`/jobs/${jobId}/psnr.json`);
    const data = await response.json();
    renderChart(data);
}
```

#### 方法 3: Data 属性

```html
<div id="chart-container" data-job-id="{{ job_id }}"></div>

<script>
const container = document.getElementById('chart-container');
const jobId = container.dataset.jobId;
</script>
```

---

## 4. 任务管理

### 4.1 同步执行短任务

对于执行时间 < 5 分钟的任务，可以**直接在 FastAPI 端点中同步执行**，无需引入 Celery/Redis。

#### 实现方式

```python
from fastapi import BackgroundTasks

@router.post("/jobs")
async def create_job(
    background_tasks: BackgroundTasks,
    # ... 其他参数
):
    job_id = str(uuid.uuid4())

    # 立即返回响应（非阻塞）
    background_tasks.add_task(process_encoding_task, job_id)

    return RedirectResponse(f"/jobs/{job_id}", status_code=303)

def process_encoding_task(job_id: str):
    """后台任务：执行编码和指标计算"""
    try:
        # 1. 更新状态为 processing
        update_task_status(job_id, "processing", progress=0)

        # 2. 执行 FFmpeg 编码
        run_ffmpeg_encoding(job_id)
        update_task_status(job_id, "processing", progress=50)

        # 3. 计算质量指标
        calculate_metrics(job_id)
        update_task_status(job_id, "processing", progress=80)

        # 4. 生成报告
        generate_report(job_id)
        update_task_status(job_id, "completed", progress=100)

    except Exception as e:
        update_task_status(job_id, "failed", error=str(e))
```

### 4.2 任务 ID 生成

```python
import uuid
from datetime import datetime

def generate_job_id() -> str:
    """生成唯一任务 ID"""
    # 方式 1: UUID4（完全随机）
    return str(uuid.uuid4())

    # 方式 2: 时间戳 + UUID（便于排序）
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    short_uuid = str(uuid.uuid4())[:8]
    return f"{timestamp}-{short_uuid}"
```

### 4.3 任务目录管理

```python
from pathlib import Path
import json

class TaskManager:
    def __init__(self, jobs_dir: Path = Path("jobs")):
        self.jobs_dir = jobs_dir
        self.jobs_dir.mkdir(exist_ok=True)

    def create_task_directory(self, job_id: str) -> Path:
        """创建任务目录"""
        task_dir = self.jobs_dir / job_id
        task_dir.mkdir(parents=True, exist_ok=True)
        return task_dir

    def save_metadata(self, job_id: str, metadata: dict):
        """保存任务元数据"""
        task_dir = self.jobs_dir / job_id
        metadata_file = task_dir / "metadata.json"

        with metadata_file.open("w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)

    def load_metadata(self, job_id: str) -> dict:
        """加载任务元数据"""
        metadata_file = self.jobs_dir / job_id / "metadata.json"

        if not metadata_file.exists():
            raise FileNotFoundError(f"任务 {job_id} 不存在")

        with metadata_file.open("r", encoding="utf-8") as f:
            return json.load(f)

    def cleanup_old_tasks(self, days: int = 7):
        """清理超过指定天数的任务"""
        from datetime import datetime, timedelta
        cutoff = datetime.now() - timedelta(days=days)

        for task_dir in self.jobs_dir.iterdir():
            if task_dir.is_dir():
                metadata = self.load_metadata(task_dir.name)
                created_at = datetime.fromisoformat(metadata["created_at"])

                if created_at < cutoff:
                    shutil.rmtree(task_dir)
```

### 4.4 任务状态管理

#### 状态定义

```python
from enum import Enum

class TaskStatus(str, Enum):
    QUEUED = "queued"          # 已创建，等待处理
    PROCESSING = "processing"  # 正在处理
    COMPLETED = "completed"    # 成功完成
    FAILED = "failed"          # 失败
```

#### 状态持久化

```python
# metadata.json 结构
{
    "job_id": "abc123",
    "status": "processing",
    "progress": 45,
    "created_at": "2025-10-25T10:30:00",
    "updated_at": "2025-10-25T10:32:15",
    "parameters": {
        "encoder_path": "/usr/bin/ffmpeg",
        "bitrate": "2000k",
        "video_filename": "test.mp4"
    },
    "error_message": null
}
```

---

## 5. 错误处理

### 5.1 表单验证

#### Pydantic 模型验证

```python
from pydantic import BaseModel, Field, validator
from pathlib import Path

class TaskCreate(BaseModel):
    encoder_path: str = Field(..., description="编码器路径")
    bitrate: Optional[str] = Field(None, pattern=r'^\d+[kKmM]$')
    crf: Optional[int] = Field(None, ge=0, le=51)
    video_filename: str

    @validator('encoder_path')
    def validate_encoder_path(cls, v):
        """验证编码器路径"""
        path = Path(v)
        if not path.exists():
            raise ValueError(f"编码器不存在: {v}")
        if not path.is_file():
            raise ValueError(f"编码器路径不是文件: {v}")
        # 可选: 检查可执行权限
        return v

    @validator('crf')
    def validate_rate_control(cls, v, values):
        """确保 bitrate 和 crf 二选一"""
        bitrate = values.get('bitrate')
        if not bitrate and v is None:
            raise ValueError("bitrate 和 crf 必须提供一个")
        if bitrate and v is not None:
            raise ValueError("bitrate 和 crf 不能同时提供")
        return v
```

#### 文件验证

```python
from fastapi import HTTPException, UploadFile
import magic  # python-magic 库

def validate_video_file(file: UploadFile):
    """验证视频文件"""
    # 1. 检查扩展名
    allowed_exts = {".mp4", ".flv", ".mov"}
    ext = Path(file.filename).suffix.lower()
    if ext not in allowed_exts:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的格式 {ext}，仅支持 {', '.join(allowed_exts)}"
        )

    # 2. 检查 MIME 类型（更安全）
    file.file.seek(0)
    mime = magic.from_buffer(file.file.read(1024), mime=True)
    file.file.seek(0)

    if not mime.startswith("video/"):
        raise HTTPException(400, "上传文件不是有效的视频文件")

    # 3. 检查文件大小
    file.file.seek(0, 2)
    size = file.file.tell()
    file.file.seek(0)

    max_size = 500 * 1024 * 1024  # 500MB
    if size > max_size:
        raise HTTPException(400, f"文件超过最大限制 500MB")
```

### 5.2 HTTPException 与自定义错误页

#### 注册全局异常处理器

```python
from fastapi import FastAPI, Request, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

app = FastAPI()
templates = Jinja2Templates(directory="backend/src/templates")

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """全局 HTTP 异常处理器"""
    # 如果是 API 请求，返回 JSON
    if request.url.path.startswith("/api/") or "application/json" in request.headers.get("accept", ""):
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail}
        )

    # 否则返回 HTML 错误页
    return templates.TemplateResponse(
        "error.html",
        {
            "request": request,
            "status_code": exc.status_code,
            "detail": exc.detail
        },
        status_code=exc.status_code
    )

@app.exception_handler(404)
async def not_found_handler(request: Request, exc: HTTPException):
    """404 自定义页面"""
    return templates.TemplateResponse(
        "404.html",
        {"request": request},
        status_code=404
    )

@app.exception_handler(500)
async def internal_error_handler(request: Request, exc: Exception):
    """500 自定义页面"""
    # 记录错误日志
    import logging
    logging.error(f"Internal error: {exc}", exc_info=True)

    return templates.TemplateResponse(
        "500.html",
        {"request": request},
        status_code=500
    )
```

#### 错误模板 (`error.html`)

```html
{% extends "base.html" %}

{% block title %}错误 {{ status_code }} - VQMR{% endblock %}

{% block content %}
<div class="max-w-2xl mx-auto text-center py-12">
    <h1 class="text-6xl font-bold text-gray-900 mb-4">{{ status_code }}</h1>
    <p class="text-xl text-gray-600 mb-8">{{ detail }}</p>

    <a href="/" class="bg-blue-600 text-white px-6 py-3 rounded-lg hover:bg-blue-700">
        返回首页
    </a>
</div>
{% endblock %}
```

### 5.3 结构化日志

```python
import logging
import json
from datetime import datetime
import uuid

class StructuredLogger:
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)

        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter('%(message)s'))
        self.logger.addHandler(handler)

    def log(self, level: str, message: str, **kwargs):
        """输出结构化 JSON 日志"""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": level.upper(),
            "message": message,
            **kwargs
        }

        self.logger.log(
            getattr(logging, level.upper()),
            json.dumps(log_entry, ensure_ascii=False)
        )

# 使用示例
logger = StructuredLogger("vqmr")

logger.log("info", "任务已创建", job_id="abc123", user_ip="192.168.1.1")
logger.log("error", "编码失败", job_id="abc123", error="FFmpeg exit code 1")
```

---

## 6. 架构图

### 6.1 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                        用户浏览器                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐          │
│  │  上传页面    │  │   报告页面   │  │   Chart.js  │          │
│  │ (upload.html)│  │(report.html) │  │   图表渲染   │          │
│  └─────────────┘  └─────────────┘  └─────────────┘          │
│         │                 │                 │                │
│         └─────────────────┴─────────────────┘                │
│                           │                                  │
└───────────────────────────┼──────────────────────────────────┘
                            │ HTTP/AJAX
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                     FastAPI 应用                             │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  API 路由层 (api/)                                      │ │
│  │  • pages.py  → GET /、GET /jobs/{id}                   │ │
│  │  • jobs.py   → POST /jobs、GET /jobs/{id}/status       │ │
│  │  • data.py   → GET /jobs/{id}/psnr.json                │ │
│  └────────────────────────────────────────────────────────┘ │
│                           │                                  │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  业务逻辑层 (services/)                                 │ │
│  │  • TaskService    → 任务生命周期管理                    │ │
│  │  • FFmpegService  → 编码执行                           │ │
│  │  • MetricsService → 指标计算与解析                      │ │
│  └────────────────────────────────────────────────────────┘ │
│                           │                                  │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  数据模型层 (models/)                                   │ │
│  │  • EncodingTask, VideoFile, MetricsResult (Pydantic)   │ │
│  └────────────────────────────────────────────────────────┘ │
└───────────────────────────┬──────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    文件系统 (jobs/)                          │
│  jobs/{job_id}/                                              │
│    ├── input.mp4       ← 上传视频                            │
│    ├── output.mp4      ← 编码输出                            │
│    ├── psnr.log        ← FFmpeg 原始日志                     │
│    ├── psnr.json       ← 解析后的 JSON                       │
│    ├── psnr.csv        ← CSV 导出                            │
│    └── metadata.json   ← 任务状态与参数                      │
└─────────────────────────────────────────────────────────────┘
```

### 6.2 请求流程

#### 创建任务流程

```
用户浏览器                FastAPI 应用               文件系统
    │                         │                        │
    │  POST /jobs             │                        │
    │  (multipart/form-data)  │                        │
    ├────────────────────────►│                        │
    │                         │                        │
    │                         │ 1. 验证表单             │
    │                         │ 2. 生成 job_id         │
    │                         │ 3. 创建任务目录         │
    │                         ├───────────────────────►│
    │                         │                        │
    │                         │ 4. 保存上传文件         │
    │                         ├───────────────────────►│
    │                         │                        │
    │                         │ 5. 启动后台任务         │
    │                         │    (BackgroundTasks)   │
    │                         │                        │
    │  303 Redirect           │                        │
    │  → /jobs/{id}           │                        │
    │◄────────────────────────┤                        │
    │                         │                        │
    │  GET /jobs/{id}         │                        │
    ├────────────────────────►│                        │
    │                         │                        │
    │                         │ 6. 加载 metadata.json  │
    │                         ├───────────────────────►│
    │                         │◄───────────────────────┤
    │                         │                        │
    │  200 HTML (report.html) │                        │
    │  status=processing      │                        │
    │◄────────────────────────┤                        │
    │                         │                        │
```

#### AJAX 轮询与数据加载

```
浏览器 (report.html)     FastAPI 应用              后台任务
    │                         │                        │
    │  (页面加载完成)          │                        │
    │  启动轮询定时器          │                        │
    │                         │                        │
    │  GET /jobs/{id}/status  │                        │
    ├────────────────────────►│                        │
    │                         │  读取 metadata.json    │
    │  200 JSON               │                        │
    │  {status: "processing"} │                        │
    │◄────────────────────────┤                        │
    │                         │                        │
    │  ... 2 秒后 ...         │                        │
    │                         │                        │
    │  GET /jobs/{id}/status  │                        │
    ├────────────────────────►│                        │
    │  200 JSON               │                        │
    │  {status: "completed"}  │                        │
    │◄────────────────────────┤                        │
    │                         │                        │
    │  检测到完成，加载数据     │                        │
    │                         │                        │
    │  GET /jobs/{id}/psnr.json│                       │
    ├────────────────────────►│                        │
    │  200 JSON (指标数据)     │                        │
    │◄────────────────────────┤                        │
    │                         │                        │
    │  渲染 Chart.js 图表      │                        │
    │                         │                        │
```

---

## 7. 完整代码示例

### 7.1 主应用入口 (`backend/src/main.py`)

```python
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathlib import Path

from .api import pages, jobs, data, health
from .config import settings

# 创建应用实例
app = FastAPI(
    title="VQMR - 视频质量指标报告",
    version="0.1.0",
    description="基于 FFmpeg 的视频质量评估系统"
)

# 挂载静态文件
app.mount("/static", StaticFiles(directory="frontend/static"), name="static")

# 注册路由
app.include_router(pages.router)
app.include_router(jobs.router)
app.include_router(data.router)
app.include_router(health.router)

# 注册异常处理器
from .api.exceptions import register_exception_handlers
register_exception_handlers(app)

# 启动事件
@app.on_event("startup")
async def startup_event():
    """应用启动时创建必要的目录"""
    jobs_dir = Path(settings.JOBS_DIR)
    jobs_dir.mkdir(exist_ok=True)
    print(f"✓ 任务目录已创建: {jobs_dir}")

# 健康检查
@app.get("/health")
async def health_check():
    return {"status": "ok", "version": "0.1.0"}
```

### 7.2 配置管理 (`backend/src/config.py`)

```python
from pydantic_settings import BaseSettings
from pathlib import Path

class Settings(BaseSettings):
    """应用配置（从环境变量加载）"""

    # 路径配置
    JOBS_DIR: Path = Path("jobs")
    TEMPLATES_DIR: Path = Path("backend/src/templates")
    STATIC_DIR: Path = Path("frontend/static")

    # FFmpeg 配置
    DEFAULT_ENCODER: str = "/usr/bin/ffmpeg"
    MAX_UPLOAD_SIZE: int = 500 * 1024 * 1024  # 500MB

    # 任务配置
    TASK_CLEANUP_DAYS: int = 7

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()
```

### 7.3 任务服务 (`backend/src/services/task.py`)

```python
from pathlib import Path
import json
import shutil
from datetime import datetime
from typing import Optional
from fastapi import UploadFile, HTTPException

from ..models.task import EncodingTask, TaskCreate, TaskStatus
from ..config import settings

class TaskService:
    def __init__(self):
        self.jobs_dir = Path(settings.JOBS_DIR)

    async def create_task(
        self,
        task_data: TaskCreate,
        video_file: UploadFile,
        reference_file: Optional[UploadFile] = None
    ) -> EncodingTask:
        """创建新任务"""
        job_id = task_data.job_id
        task_dir = self.jobs_dir / job_id
        task_dir.mkdir(parents=True, exist_ok=True)

        # 保存上传文件
        input_path = task_dir / "input.mp4"
        await self._save_upload_file(video_file, input_path)

        if reference_file:
            ref_path = task_dir / "reference.mp4"
            await self._save_upload_file(reference_file, ref_path)

        # 创建元数据
        metadata = {
            "job_id": job_id,
            "status": TaskStatus.QUEUED,
            "progress": 0,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "parameters": task_data.dict(exclude={"job_id"}),
            "error_message": None
        }

        self._save_metadata(job_id, metadata)

        return EncodingTask(**metadata)

    async def get_task(self, job_id: str) -> EncodingTask:
        """获取任务信息"""
        metadata = self._load_metadata(job_id)
        return EncodingTask(**metadata)

    async def update_task_status(
        self,
        job_id: str,
        status: TaskStatus,
        progress: int = 0,
        error_message: Optional[str] = None
    ):
        """更新任务状态"""
        metadata = self._load_metadata(job_id)
        metadata.update({
            "status": status,
            "progress": progress,
            "updated_at": datetime.utcnow().isoformat(),
            "error_message": error_message
        })
        self._save_metadata(job_id, metadata)

    def _save_metadata(self, job_id: str, metadata: dict):
        """保存元数据到 JSON 文件"""
        metadata_file = self.jobs_dir / job_id / "metadata.json"
        with metadata_file.open("w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)

    def _load_metadata(self, job_id: str) -> dict:
        """加载元数据"""
        metadata_file = self.jobs_dir / job_id / "metadata.json"

        if not metadata_file.exists():
            raise HTTPException(404, f"任务 {job_id} 不存在")

        with metadata_file.open("r", encoding="utf-8") as f:
            return json.load(f)

    async def _save_upload_file(self, upload_file: UploadFile, destination: Path):
        """流式保存上传文件"""
        with destination.open("wb") as buffer:
            shutil.copyfileobj(upload_file.file, buffer)
```

### 7.4 数据模型 (`backend/src/models/task.py`)

```python
from pydantic import BaseModel, Field, validator
from enum import Enum
from typing import Optional
from datetime import datetime

class TaskStatus(str, Enum):
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class TaskCreate(BaseModel):
    """创建任务请求"""
    job_id: str
    encoder_path: str
    bitrate: Optional[str] = None
    crf: Optional[int] = Field(None, ge=0, le=51)
    video_filename: str

    @validator('crf')
    def validate_rate_control(cls, v, values):
        """确保 bitrate 和 crf 二选一"""
        bitrate = values.get('bitrate')
        if not bitrate and v is None:
            raise ValueError("bitrate 和 crf 必须提供一个")
        return v

class EncodingTask(BaseModel):
    """任务实体"""
    job_id: str
    status: TaskStatus
    progress: int = Field(ge=0, le=100)
    created_at: datetime
    updated_at: datetime
    parameters: dict
    error_message: Optional[str] = None
```

---

## 8. 最佳实践清单

### 8.1 架构设计

- [ ] 使用分层架构（API → Services → Models）
- [ ] 路由按功能模块拆分（pages/jobs/data）
- [ ] 静态文件与模板分离目录管理
- [ ] 任务数据按 job_id 独立目录存储
- [ ] 配置通过环境变量管理（`.env` 文件）

### 8.2 路由与 API

- [ ] 页面路由返回 `HTMLResponse`（Jinja2 模板）
- [ ] 数据 API 返回 `JSONResponse`
- [ ] 使用 `RedirectResponse` + 303 状态码处理 POST 后重定向
- [ ] API 路由添加 `prefix` 和 `tags`（便于文档生成）
- [ ] 健康检查端点返回版本号

### 8.3 表单与文件上传

- [ ] 安装 `python-multipart` 依赖
- [ ] 表单字段使用 `Form()` 声明
- [ ] 文件上传使用 `UploadFile` 类型
- [ ] 文件操作端点用 `def` 而非 `async def`
- [ ] 验证文件扩展名、MIME 类型、大小
- [ ] 流式保存文件（避免内存溢出）

### 8.4 模板引擎

- [ ] 使用模板继承（base.html → 子模板）
- [ ] 传递 `request` 对象到所有模板
- [ ] CDN 资源放在 `<head>` 中（Tailwind/Chart.js）
- [ ] 自定义样式/脚本通过 `/static` 挂载
- [ ] 数据传递优先用 AJAX（而非内联 JSON）

### 8.5 错误处理

- [ ] 使用 Pydantic 验证器验证表单数据
- [ ] 注册全局异常处理器（区分 API/页面请求）
- [ ] 404/500 错误返回自定义 HTML 页面
- [ ] 记录结构化日志（JSON 格式，包含 job_id）
- [ ] 捕获所有异常并返回友好错误信息

### 8.6 任务管理

- [ ] 使用 `BackgroundTasks` 执行短任务
- [ ] 任务状态持久化到 `metadata.json`
- [ ] 提供状态查询接口（供 AJAX 轮询）
- [ ] 实现任务清理机制（定时删除过期任务）
- [ ] 任务目录权限控制（避免路径遍历攻击）

### 8.7 性能与安全

- [ ] 限制上传文件大小（防止 DoS 攻击）
- [ ] 验证用户输入（编码器路径、文件路径）
- [ ] 生产环境用 Uvicorn + Gunicorn 部署
- [ ] 静态文件由 Nginx 服务（性能优化）
- [ ] 启用 CORS（如需跨域 API 调用）

---

## 9. 与 Django/Flask 对比

### 9.1 功能对比表

| 特性 | FastAPI + Jinja2 | Django | Flask + Jinja2 |
|------|-----------------|--------|----------------|
| **学习曲线** | 中等（需理解 async） | 陡峭（ORM/Admin） | 平缓 |
| **类型提示** | ✅ 原生支持（Pydantic） | ❌ 需额外库 | ❌ 需额外库 |
| **性能** | 高（ASGI 异步） | 中（WSGI 同步） | 中（WSGI 同步） |
| **API 文档** | ✅ 自动生成（OpenAPI） | ❌ 需手动编写 | ❌ 需手动编写 |
| **模板引擎** | Jinja2（需手动集成） | Django Templates | Jinja2（内置） |
| **ORM** | ❌ 需额外库（SQLAlchemy） | ✅ 内置 Django ORM | ❌ 需 SQLAlchemy |
| **Admin 后台** | ❌ 无 | ✅ 强大的 Admin | ❌ 需 Flask-Admin |
| **表单验证** | Pydantic | Django Forms | WTForms |
| **适用场景** | API 优先 + 轻量 SSR | 全栈企业应用 | 灵活轻量应用 |

### 9.2 代码对比

#### 创建任务端点

**FastAPI**:
```python
@router.post("/jobs")
async def create_job(
    encoder_path: str = Form(...),
    video_file: UploadFile = File(...)
):
    # 自动类型验证、自动文档生成
    job_id = str(uuid.uuid4())
    return RedirectResponse(f"/jobs/{job_id}", status_code=303)
```

**Django**:
```python
def create_job(request):
    if request.method == 'POST':
        form = JobForm(request.POST, request.FILES)
        if form.is_valid():
            job = form.save()
            return redirect('job_detail', pk=job.id)
    # 需要 forms.py、models.py、urls.py 配置
```

**Flask**:
```python
@app.route('/jobs', methods=['POST'])
def create_job():
    encoder_path = request.form['encoder_path']
    video_file = request.files['video_file']
    # 手动验证、手动保存
    job_id = str(uuid.uuid4())
    return redirect(f'/jobs/{job_id}')
```

### 9.3 选型建议

| 需求 | 推荐框架 | 理由 |
|------|---------|------|
| API 为主 + 少量页面 | **FastAPI** | 自动文档、类型安全、高性能 |
| 传统 CRUD 后台 | **Django** | ORM + Admin 省开发时间 |
| 微服务/原型 | **Flask** | 轻量灵活 |
| 实时应用（WebSocket） | **FastAPI** | ASGI 原生支持 |
| 大量数据库操作 | **Django** | 成熟的 ORM 和迁移工具 |

### 9.4 FastAPI SSR 的优势

1. **类型安全**: Pydantic 自动验证请求参数
2. **自动文档**: 即使是 SSR 应用，数据 API 仍有完整文档
3. **异步性能**: 处理文件上传时不阻塞其他请求
4. **现代化**: 支持 async/await、依赖注入
5. **灵活性**: 同一应用同时提供 HTML 和 JSON API

### 9.5 FastAPI SSR 的劣势

1. **生态不成熟**: 缺少成熟的表单库（不如 Django Forms）
2. **无内置 ORM**: 需额外集成 SQLAlchemy
3. **模板功能弱**: Jinja2 集成较简单，不如 Django Templates 强大
4. **学习曲线**: 需理解 async/await、依赖注入等概念
5. **不适合复杂后台**: 无内置 Admin，构建复杂后台成本高

---

## 10. 总结与建议

### 10.1 VQMR 项目适配性

对于 VQMR 视频质量指标报告系统，**FastAPI + Jinja2 SSR 架构非常合适**，原因：

1. **轻量需求**: 仅 3 个页面（上传/报告/错误），无需 Django 的重量级功能
2. **API 优先**: 需要 JSON API（`/jobs/{id}/psnr.json`）供前端图表使用
3. **类型安全**: 编���参数验证复杂，Pydantic 可大幅减少错误
4. **自动文档**: API 文档自动生成，便于调试和对接
5. **文件处理**: `UploadFile` + async 可高效处理大视频文件

### 10.2 架构建议

```text
推荐架构:
- 后端: FastAPI (API + Jinja2 SSR 页面)
- 前端: Tailwind CDN + Chart.js CDN + 原生 JS
- 存储: 文件系统（任务数据按 job_id 分桶）
- 任务: BackgroundTasks（短任务同步执行）
- 部署: Docker + Nginx（Nginx 代理 + 静态文件服务）
```

### 10.3 下一步行动

1. **搭建基础框架**: 按本文档目录结构创建项目骨架
2. **实现上传页面**: 表单 + 文件上传 + 验证
3. **实现任务管理**: 后台任务执行 + 状态持久化
4. **实现报告页面**: Jinja2 模板 + Chart.js 图表
5. **集成 FFmpeg**: 调用 FFmpeg 执行编码和指标计算
6. **编写测试**: 契约测试（API）+ 集成测试（用户流程）
7. **容器化部署**: Dockerfile + docker-compose.yml

---

**文档版本**: 1.0
**最后更新**: 2025-10-25
**参考资源**:
- [FastAPI 官方文档 - Templates](https://fastapi.tiangolo.com/advanced/templates/)
- [FastAPI 官方文档 - Request Files](https://fastapi.tiangolo.com/tutorial/request-files/)
- [Jinja2 官方文档](https://jinja.palletsprojects.com/)
- [Chart.js 官方文档](https://www.chartjs.org/)
- [Tailwind CSS 官方文档](https://tailwindcss.com/)
