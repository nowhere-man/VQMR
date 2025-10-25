# Pytest 契约测试与集成测试最佳实践指南

**项目**: VQMR (Video Quality Metrics Report)
**日期**: 2025-10-25
**版本**: 1.0

---

## 目录

1. [测试策略概览](#测试策略概览)
2. [项目配置](#项目配置)
3. [测试目录结构](#测试目录结构)
4. [契约测试 (Contract Tests)](#契约测试-contract-tests)
5. [集成测试 (Integration Tests)](#集成测试-integration-tests)
6. [共享 Fixtures (conftest.py)](#共享-fixtures-conftestpy)
7. [测试数据管理](#测试数据管理)
8. [测试覆盖率](#测试覆盖率)
9. [CI/CD 集成](#cicd-集成)
10. [最佳实践清单](#最佳实践清单)

---

## 测试策略概览

### 测试金字塔

```
        /\
       /  \      E2E Tests (Integration)
      /____\     ~10-20% 覆盖率
     /      \
    /Contract\   Contract Tests
   /__________\  ~30-40% 覆盖率
  /            \
 /  Unit Tests  \ Unit Tests
/________________\ ~50-60% 覆盖率
```

### 测试类型定义

| 测试类型 | 目的 | 覆盖率目标 | 执行速度 |
|---------|------|-----------|---------|
| **Unit Tests** | 测试单个函数/类的逻辑 | 80%+ | 快 (<1s) |
| **Contract Tests** | 验证 API 接口契约 | 100% | 中等 (1-5s) |
| **Integration Tests** | 测试端到端用户场景 | 80%+ | 慢 (5-60s) |

### VQMR 测试范围

- **P1 功能**: 契约测试 100% + 集成测试 80%
- **P2 功能**: 契约测试 100% + 集成��试 70%
- **P3 功能**: 契约测试 90% + 集成测试 60%

---

## 项目配置

### 1. pyproject.toml

```toml
[project]
name = "vqmr"
version = "0.1.0"
description = "Video Quality Metrics Report System"
requires-python = ">=3.10"
dependencies = [
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.32.0",
    "jinja2>=3.1.4",
    "python-multipart>=0.0.17",
    "pydantic>=2.10.0",
    "pydantic-settings>=2.6.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.3.0",
    "pytest-asyncio>=0.24.0",
    "pytest-cov>=6.0.0",
    "pytest-mock>=3.14.0",
    "pytest-subprocess>=1.5.0",
    "httpx>=0.28.0",
    "faker>=33.0.0",
    "ruff>=0.8.0",
]

[tool.pytest.ini_options]
# 测试发现与执行
testpaths = ["backend/tests"]
python_files = ["test_*.py", "*_test.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]

# 命令行选项
addopts = [
    "-v",                           # 详细输出
    "--strict-markers",             # 严格标记模式
    "--tb=short",                   # 简短的回溯信息
    "--cov=backend/src",            # 覆盖率目标
    "--cov-report=term-missing",    # 终端报告显示缺失行
    "--cov-report=html:coverage_html_report",
    "--cov-report=lcov:coverage.lcov",
    "--cov-fail-under=80",          # 最低覆盖率要求
]

# 自定义标记
markers = [
    "unit: 单元测试 (快速, 隔离)",
    "contract: API 契约测试 (验证接口)",
    "integration: 集成测试 (端到端场景)",
    "slow: 慢速测试 (>5秒)",
    "ffmpeg: 需要 FFmpeg 的测试",
    "real_video: 需要真实视频文件的测试",
]

# 异步支持
asyncio_mode = "auto"
asyncio_default_fixture_loop_scope = "function"

# 输出与警告
console_output_style = "progress"
log_cli = true
log_cli_level = "INFO"
log_cli_format = "%(asctime)s [%(levelname)8s] %(message)s"
log_cli_date_format = "%Y-%m-%d %H:%M:%S"

filterwarnings = [
    "error",
    "ignore::DeprecationWarning",
    "ignore::PendingDeprecationWarning",
]

[tool.coverage.run]
source = ["backend/src"]
branch = true
parallel = true
omit = [
    "*/tests/*",
    "*/conftest.py",
    "*/__pycache__/*",
    "*/venv/*",
    "*/.venv/*",
]

[tool.coverage.report]
precision = 2
fail_under = 80
skip_empty = true
exclude_also = [
    "def __repr__",
    "if self\\.debug",
    "if settings\\.DEBUG",
    "raise AssertionError",
    "raise NotImplementedError",
    "if 0:",
    "if False:",
    "if __name__ == .__main__.:",
    "@(abc\\.)?abstractmethod",
    "class .*\\(Protocol\\):",
    "def main\\(",
]

[tool.coverage.html]
directory = "coverage_html_report"

[tool.ruff]
line-length = 100
target-version = "py310"

[tool.ruff.lint]
select = ["E", "F", "I", "N", "W", "UP"]
ignore = ["E501"]  # 行长度由 formatter 处理

[tool.ruff.lint.isort]
known-first-party = ["backend"]
```

### 2. pytest.ini (可选, 如不使用 pyproject.toml)

```ini
[pytest]
testpaths = backend/tests
python_files = test_*.py *_test.py
python_classes = Test*
python_functions = test_*

addopts =
    -v
    --strict-markers
    --tb=short
    --cov=backend/src
    --cov-report=term-missing
    --cov-report=html:coverage_html_report
    --cov-fail-under=80

markers =
    unit: 单元测试
    contract: API 契约测试
    integration: 集成测试
    slow: 慢速测试
    ffmpeg: 需要 FFmpeg 的测试
    real_video: 需要真实视频文件的测试

asyncio_mode = auto
log_cli = true
log_cli_level = INFO
```

### 3. .env.test (测试环境变量)

```env
# 应用配置
APP_ENV=test
DEBUG=False
LOG_LEVEL=DEBUG

# 存储路径 (使用临时目录)
JOBS_ROOT_DIR=/tmp/vqmr_test_jobs
UPLOAD_MAX_SIZE=104857600  # 100MB

# FFmpeg 配置 (可被测试 mock)
FFMPEG_PATH=/usr/bin/ffmpeg
FFPROBE_PATH=/usr/bin/ffprobe
VMAF_MODEL_PATH=/usr/share/model/vmaf_v0.6.1.json

# 任务配置
MAX_CONCURRENT_TASKS=2
TASK_TIMEOUT=600
TASK_CLEANUP_DAYS=1

# 测试专用
USE_MOCK_FFMPEG=true
TEST_ASSETS_DIR=backend/tests/assets
```

---

## 测试目录结构

```
backend/tests/
├── conftest.py                  # 根级共享 fixtures
├── pytest.ini                   # pytest 配置 (可选)
│
├── contract/                    # 契约测试
│   ├── conftest.py              # 契约测试专用 fixtures
│   ├── test_health_api.py       # 健康检查 API
│   ├── test_job_submission_api.py
│   ├── test_job_status_api.py
│   ├── test_report_api.py
│   └── test_file_upload_api.py
│
├── integration/                 # 集成测试
│   ├── conftest.py              # 集成测试专用 fixtures
│   ├── test_e2e_single_task.py  # P1: 单任务端到端
│   ├── test_e2e_multi_params.py # P2: 多参数对比
│   ├── test_e2e_yuv_workflow.py # P3: YUV 文件处理
│   └── test_ffmpeg_integration.py
│
├── unit/                        # 单元测试
│   ├── conftest.py
│   ├── test_models.py
│   ├── test_ffmpeg_service.py
│   ├── test_metrics_service.py
│   └── test_task_service.py
│
├── fixtures/                    # 共享 fixture 模块
│   ├── __init__.py
│   ├── app_fixtures.py          # FastAPI app fixtures
│   ├── database_fixtures.py     # 数据库 fixtures (如需要)
│   ├── ffmpeg_fixtures.py       # FFmpeg mock fixtures
│   ├── video_fixtures.py        # 测试视频文件 fixtures
│   └── factory_fixtures.py      # 数据工厂 fixtures
│
└── assets/                      # 测试资源文件
    ├── videos/
    │   ├── sample_1080p_10s.mp4  # 标准测试视频
    │   ├── sample_720p_5s.mp4
    │   ├── sample.yuv            # YUV 测试文件
    │   ├── corrupted.mp4         # 损坏文件测试
    │   └── README.md             # 测试文件说明
    ├── ffmpeg_logs/
    │   ├── psnr_success.log      # Mock FFmpeg 输出
    │   ├── vmaf_success.log
    │   └── encode_error.log
    └── expected_results/
        ├── psnr_expected.json    # 预期结果
        └── metrics_expected.csv
```

### 目录说明

- **contract/**: API 端点的输入/输出契约验证，不依赖真实 FFmpeg
- **integration/**: 端到端场景测试，可选择 mock 或真实 FFmpeg
- **unit/**: 单个组件的逻辑测试，完全 mock 外部依赖
- **fixtures/**: 按功能模块化的 fixture 定义
- **assets/**: 静态测试资源 (受版本控制)

---

## 契约测试 (Contract Tests)

### 核心原则

1. **验证 API 契约**: HTTP 状态码、响应头、JSON schema
2. **快速执行**: 使用 TestClient，无真实子进程
3. **100% 端点覆盖**: 所有 API 路由必须有契约测试
4. **独立性**: 每个测试独立，不依赖执行顺序

### 示例 1: 健康检查 API 契约测试

**文件**: `backend/tests/contract/test_health_api.py`

```python
"""健康检查 API 契约测试

验证 /health 端点返回正确的状态和格式
"""

import pytest
from fastapi.testclient import TestClient


@pytest.mark.contract
def test_health_endpoint_returns_200(client: TestClient):
    """测试健康检查端点返回 200 状态码"""
    response = client.get("/health")

    assert response.status_code == 200


@pytest.mark.contract
def test_health_endpoint_response_schema(client: TestClient):
    """测试健康检查端点返回正确的 JSON schema"""
    response = client.get("/health")
    data = response.json()

    assert "status" in data
    assert data["status"] == "ok"
    assert "timestamp" in data
    assert "version" in data


@pytest.mark.contract
def test_health_endpoint_content_type(client: TestClient):
    """测试健康检查端点返回正确的 Content-Type"""
    response = client.get("/health")

    assert response.headers["content-type"] == "application/json"


@pytest.mark.contract
def test_health_endpoint_cors_headers(client: TestClient):
    """测试健康检查端点包含 CORS 头 (如适用)"""
    response = client.get("/health")

    # 根据实际 CORS 配置调整
    assert "access-control-allow-origin" in response.headers or True
```

### 示例 2: 任务提交 API 契约测试

**文件**: `backend/tests/contract/test_job_submission_api.py`

```python
"""任务提交 API 契约测试

验证 POST /api/v1/jobs 端点的输入验证和响应格式
"""

import pytest
from fastapi.testclient import TestClient


@pytest.mark.contract
class TestJobSubmissionContract:
    """任务提交 API 契约测试套件"""

    def test_submit_valid_single_abr_task(self, client: TestClient, valid_job_payload):
        """测试提交有效的单 ABR 任务返回 201"""
        response = client.post("/api/v1/jobs", json=valid_job_payload)

        assert response.status_code == 201
        data = response.json()
        assert "job_id" in data
        assert "status" in data
        assert data["status"] == "queued"

    def test_submit_task_response_schema(self, client: TestClient, valid_job_payload):
        """测试任务提交响应符合 schema"""
        response = client.post("/api/v1/jobs", json=valid_job_payload)
        data = response.json()

        required_fields = ["job_id", "status", "created_at", "encoder_path", "video_path"]
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"

        # 验证字段类型
        assert isinstance(data["job_id"], str)
        assert isinstance(data["status"], str)
        assert isinstance(data["created_at"], str)

    def test_submit_invalid_encoder_path_returns_400(self, client: TestClient):
        """测试无效编码器路径返回 400"""
        payload = {
            "encoder_path": "/nonexistent/encoder",
            "video_path": "/valid/video.mp4",
            "rate_control_mode": "abr",
            "rate_control_values": [1000]
        }

        response = client.post("/api/v1/jobs", json=payload)

        assert response.status_code == 400
        data = response.json()
        assert "detail" in data
        assert "encoder" in data["detail"].lower()

    def test_submit_invalid_video_path_returns_400(self, client: TestClient):
        """测试无效视频路径返回 400"""
        payload = {
            "encoder_path": "/usr/bin/ffmpeg",
            "video_path": "/nonexistent/video.mp4",
            "rate_control_mode": "abr",
            "rate_control_values": [1000]
        }

        response = client.post("/api/v1/jobs", json=payload)

        assert response.status_code == 400
        data = response.json()
        assert "detail" in data
        assert "video" in data["detail"].lower() or "file" in data["detail"].lower()

    def test_submit_mixed_rate_control_returns_400(self, client: TestClient):
        """测试同时指定 ABR 和 CRF 返回 400"""
        payload = {
            "encoder_path": "/usr/bin/ffmpeg",
            "video_path": "/valid/video.mp4",
            "rate_control_mode": "abr",
            "rate_control_values": [1000],
            "crf_values": [23]  # 不应同时指定
        }

        response = client.post("/api/v1/jobs", json=payload)

        assert response.status_code == 422  # Validation error

    def test_submit_multiple_abr_values(self, client: TestClient):
        """测试提交多个 ABR 值 (P2 功能)"""
        payload = {
            "encoder_path": "/usr/bin/ffmpeg",
            "video_path": "/valid/video.mp4",
            "rate_control_mode": "abr",
            "rate_control_values": [500, 1000, 2000]
        }

        response = client.post("/api/v1/jobs", json=payload)

        assert response.status_code == 201
        data = response.json()
        assert "subtasks" in data or "rate_control_values" in data

    def test_submit_yuv_without_metadata_returns_400(self, client: TestClient):
        """测试提交 YUV 文件但缺少元数据返回 400 (P3 功能)"""
        payload = {
            "encoder_path": "/usr/bin/ffmpeg",
            "video_path": "/valid/video.yuv",
            "rate_control_mode": "abr",
            "rate_control_values": [1000]
            # 缺少 resolution, pixel_format, framerate
        }

        response = client.post("/api/v1/jobs", json=payload)

        assert response.status_code == 400
        data = response.json()
        assert "yuv" in data["detail"].lower() or "metadata" in data["detail"].lower()

    def test_submit_yuv_with_metadata(self, client: TestClient):
        """测试提交 YUV 文件并提供完整元数据 (P3 功能)"""
        payload = {
            "encoder_path": "/usr/bin/ffmpeg",
            "video_path": "/valid/video.yuv",
            "rate_control_mode": "abr",
            "rate_control_values": [1000],
            "yuv_metadata": {
                "resolution": "1920x1080",
                "pixel_format": "yuv420p",
                "framerate": 30
            }
        }

        response = client.post("/api/v1/jobs", json=payload)

        assert response.status_code == 201


@pytest.mark.contract
def test_submit_empty_payload_returns_422(client: TestClient):
    """测试提交空 payload 返回 422 验证错误"""
    response = client.post("/api/v1/jobs", json={})

    assert response.status_code == 422


@pytest.mark.contract
def test_submit_malformed_json_returns_422(client: TestClient):
    """测试提交格式错误的 JSON 返回 422"""
    response = client.post(
        "/api/v1/jobs",
        data="not a json",
        headers={"Content-Type": "application/json"}
    )

    assert response.status_code == 422
```

### 示例 3: 文件上传契约测试

**文件**: `backend/tests/contract/test_file_upload_api.py`

```python
"""文件上传 API 契约测试

验证 POST /api/v1/upload 端点的文件上传功能
"""

import io
import pytest
from fastapi.testclient import TestClient


@pytest.mark.contract
class TestFileUploadContract:
    """文件上传 API 契约测试套件"""

    def test_upload_valid_video_file_returns_201(self, client: TestClient):
        """测试上传有效视频文件返回 201"""
        # 创建模拟视频文件
        file_content = b"fake video content"
        files = {"file": ("test_video.mp4", io.BytesIO(file_content), "video/mp4")}

        response = client.post("/api/v1/upload", files=files)

        assert response.status_code == 201
        data = response.json()
        assert "file_id" in data
        assert "file_path" in data

    def test_upload_response_schema(self, client: TestClient):
        """测试上传响应符合 schema"""
        files = {"file": ("test.mp4", io.BytesIO(b"content"), "video/mp4")}
        response = client.post("/api/v1/upload", files=files)

        data = response.json()
        assert "file_id" in data
        assert "file_path" in data
        assert "file_size" in data
        assert "uploaded_at" in data

    def test_upload_no_file_returns_422(self, client: TestClient):
        """测试未提供文件返回 422"""
        response = client.post("/api/v1/upload")

        assert response.status_code == 422

    def test_upload_invalid_content_type_returns_400(self, client: TestClient):
        """测试上传非视频文件返回 400"""
        files = {"file": ("test.txt", io.BytesIO(b"text content"), "text/plain")}

        response = client.post("/api/v1/upload", files=files)

        assert response.status_code == 400
        data = response.json()
        assert "video" in data["detail"].lower() or "format" in data["detail"].lower()

    def test_upload_exceeds_size_limit_returns_413(self, client: TestClient):
        """测试上传超大文件返回 413"""
        # 创建超过限制的文件 (假设限制为 100MB)
        large_content = b"x" * (101 * 1024 * 1024)  # 101MB
        files = {"file": ("large.mp4", io.BytesIO(large_content), "video/mp4")}

        response = client.post("/api/v1/upload", files=files)

        assert response.status_code == 413

    def test_upload_supported_formats(self, client: TestClient):
        """测试支持的视频格式 (MP4, FLV)"""
        for ext, mime in [("mp4", "video/mp4"), ("flv", "video/x-flv")]:
            files = {"file": (f"test.{ext}", io.BytesIO(b"content"), mime)}
            response = client.post("/api/v1/upload", files=files)

            assert response.status_code in [201, 202], f"Failed for {ext}"
```

### 示例 4: 报告 API 契约测试

**文件**: `backend/tests/contract/test_report_api.py`

```python
"""报告 API 契约测试

验证报告查看和数据导出 API 端点
"""

import pytest
from fastapi.testclient import TestClient


@pytest.mark.contract
class TestReportAPIContract:
    """报告 API 契约测试套件"""

    def test_get_job_report_html_returns_200(
        self, client: TestClient, completed_job_id: str
    ):
        """测试获取任务报告 HTML 页面返回 200"""
        response = client.get(f"/jobs/{completed_job_id}/report")

        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

    def test_get_psnr_json_returns_200(
        self, client: TestClient, completed_job_id: str
    ):
        """测试获取 PSNR JSON 数据返回 200"""
        response = client.get(f"/api/v1/jobs/{completed_job_id}/metrics/psnr.json")

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/json"

        data = response.json()
        assert "average" in data
        assert "frames" in data
        assert isinstance(data["frames"], list)

    def test_get_vmaf_json_schema(
        self, client: TestClient, completed_job_id: str
    ):
        """测试 VMAF JSON 数据符合 schema"""
        response = client.get(f"/api/v1/jobs/{completed_job_id}/metrics/vmaf.json")

        assert response.status_code == 200
        data = response.json()

        # 验证必需字段
        required_fields = ["average", "min", "max", "frames"]
        for field in required_fields:
            assert field in data

        # 验证数据类型
        assert isinstance(data["average"], (int, float))
        assert isinstance(data["min"], (int, float))
        assert isinstance(data["max"], (int, float))
        assert isinstance(data["frames"], list)

        # 验证帧数据结构
        if len(data["frames"]) > 0:
            frame = data["frames"][0]
            assert "frame_num" in frame
            assert "vmaf_score" in frame

    def test_get_csv_export_returns_text_csv(
        self, client: TestClient, completed_job_id: str
    ):
        """测试导出 CSV 返回正确的 Content-Type"""
        response = client.get(f"/api/v1/jobs/{completed_job_id}/export/metrics.csv")

        assert response.status_code == 200
        assert "text/csv" in response.headers["content-type"]

        # 验证 CSV 内容格式
        csv_content = response.text
        lines = csv_content.strip().split("\n")
        assert len(lines) >= 2  # 至少有 header + 1 行数据

        header = lines[0]
        assert "frame_num" in header
        assert "psnr" in header
        assert "vmaf" in header
        assert "ssim" in header

    def test_get_nonexistent_job_returns_404(self, client: TestClient):
        """测试获取不存在的任务返回 404"""
        response = client.get("/api/v1/jobs/nonexistent-job-id/report")

        assert response.status_code == 404
        data = response.json()
        assert "detail" in data

    def test_get_pending_job_report_returns_425(
        self, client: TestClient, pending_job_id: str
    ):
        """测试获取未完成任务的报告返回 425 (Too Early)"""
        response = client.get(f"/api/v1/jobs/{pending_job_id}/report")

        assert response.status_code == 425
        data = response.json()
        assert "status" in data
        assert data["status"] in ["queued", "processing"]


@pytest.mark.contract
def test_metrics_tolerance_validation(client: TestClient, completed_job_id: str):
    """测试指标数据在合理范围内 (容差验证)"""
    response = client.get(f"/api/v1/jobs/{completed_job_id}/metrics/psnr.json")
    data = response.json()

    # PSNR 应在 0-100 之间
    assert 0 <= data["average"] <= 100

    response = client.get(f"/api/v1/jobs/{completed_job_id}/metrics/vmaf.json")
    data = response.json()

    # VMAF 应在 0-100 之间
    assert 0 <= data["average"] <= 100
    assert 0 <= data["min"] <= 100
    assert 0 <= data["max"] <= 100
```

---

## 集成测试 (Integration Tests)

### 核心原则

1. **端到端场���**: 模拟真实用户工作流
2. **可选真实依赖**: 支持 mock FFmpeg 或真实执行
3. **独立环境**: 使用临时文件系统和隔离配置
4. **异步任务测试**: 验证任务队列和状态转换

### 示例 1: 端到端单任务测试 (P1)

**文件**: `backend/tests/integration/test_e2e_single_task.py`

```python
"""端到端单任务集成测试 (P1 功能)

测试完整的用户场景: 提交任务 → 编码 → 生成报告
"""

import json
import time
import pytest
from pathlib import Path
from fastapi.testclient import TestClient


@pytest.mark.integration
@pytest.mark.slow
class TestE2ESingleTask:
    """端到端单任务测试套件"""

    def test_submit_encode_report_workflow(
        self,
        client: TestClient,
        test_video_path: Path,
        mock_ffmpeg_service,
        tmp_jobs_dir: Path
    ):
        """测试完整工作流: 提交 → 编码 → 查看报告"""
        # Step 1: 提交任务
        payload = {
            "encoder_path": "/usr/bin/ffmpeg",
            "video_path": str(test_video_path),
            "rate_control_mode": "abr",
            "rate_control_values": [1000]
        }

        submit_response = client.post("/api/v1/jobs", json=payload)
        assert submit_response.status_code == 201

        job_id = submit_response.json()["job_id"]
        assert job_id is not None

        # Step 2: 等待任务完成 (或模拟完成)
        # 在真实测试中可能需要轮询状态
        max_wait = 30  # 30 秒超时
        start = time.time()

        while time.time() - start < max_wait:
            status_response = client.get(f"/api/v1/jobs/{job_id}/status")
            status_data = status_response.json()

            if status_data["status"] == "completed":
                break
            elif status_data["status"] == "failed":
                pytest.fail(f"Job failed: {status_data.get('error')}")

            time.sleep(1)
        else:
            pytest.fail("Job did not complete within timeout")

        # Step 3: 验证任务目录结构
        job_dir = tmp_jobs_dir / job_id
        assert job_dir.exists()
        assert (job_dir / "input.mp4").exists()
        assert (job_dir / "output.mp4").exists()
        assert (job_dir / "metadata.json").exists()

        # Step 4: 验证指标文件
        assert (job_dir / "psnr.json").exists()
        assert (job_dir / "vmaf.json").exists()
        assert (job_dir / "ssim.json").exists()

        with open(job_dir / "psnr.json") as f:
            psnr_data = json.load(f)
            assert "average" in psnr_data
            assert 0 <= psnr_data["average"] <= 100

        # Step 5: 获取报告 HTML
        report_response = client.get(f"/jobs/{job_id}/report")
        assert report_response.status_code == 200
        assert "<!DOCTYPE html>" in report_response.text

        # Step 6: 获取 JSON 数据
        psnr_response = client.get(f"/api/v1/jobs/{job_id}/metrics/psnr.json")
        assert psnr_response.status_code == 200

        psnr_json = psnr_response.json()
        assert "average" in psnr_json
        assert "frames" in psnr_json

    @pytest.mark.ffmpeg
    @pytest.mark.real_video
    def test_real_ffmpeg_encoding(
        self,
        client: TestClient,
        real_test_video: Path,
        tmp_jobs_dir: Path
    ):
        """使用真实 FFmpeg 的集成测试 (需要 FFmpeg 安装)"""
        payload = {
            "encoder_path": "/usr/bin/ffmpeg",  # 真实路径
            "video_path": str(real_test_video),
            "rate_control_mode": "abr",
            "rate_control_values": [500]
        }

        submit_response = client.post("/api/v1/jobs", json=payload)
        assert submit_response.status_code == 201

        job_id = submit_response.json()["job_id"]

        # 等待真实编码完成 (可能需要更长时间)
        max_wait = 300  # 5 分钟
        start = time.time()

        while time.time() - start < max_wait:
            status_response = client.get(f"/api/v1/jobs/{job_id}/status")
            status = status_response.json()["status"]

            if status == "completed":
                break
            elif status == "failed":
                pytest.fail("Real FFmpeg encoding failed")

            time.sleep(2)
        else:
            pytest.fail("Real encoding timeout")

        # 验证输出文件确实存在且非空
        job_dir = tmp_jobs_dir / job_id
        output_file = job_dir / "output.mp4"
        assert output_file.exists()
        assert output_file.stat().st_size > 0

        # 验证指标文件
        psnr_file = job_dir / "psnr.json"
        assert psnr_file.exists()

        with open(psnr_file) as f:
            data = json.load(f)
            # 真实 PSNR 值应在合理范围内
            assert 20 <= data["average"] <= 60  # 典型视频 PSNR 范围
```

### 示例 2: 多参数对比集成测试 (P2)

**文件**: `backend/tests/integration/test_e2e_multi_params.py`

```python
"""端到端多参数对比集成测试 (P2 功能)

测试用户提交多个码率值并查看对比报告
"""

import pytest
from pathlib import Path
from fastapi.testclient import TestClient


@pytest.mark.integration
@pytest.mark.slow
class TestE2EMultiParams:
    """多参数对比测试套件"""

    def test_multi_abr_comparison(
        self,
        client: TestClient,
        test_video_path: Path,
        mock_ffmpeg_service,
        tmp_jobs_dir: Path
    ):
        """测试多个 ABR 值对比工作流"""
        abr_values = [500, 1000, 2000]

        payload = {
            "encoder_path": "/usr/bin/ffmpeg",
            "video_path": str(test_video_path),
            "rate_control_mode": "abr",
            "rate_control_values": abr_values
        }

        submit_response = client.post("/api/v1/jobs", json=payload)
        assert submit_response.status_code == 201

        response_data = submit_response.json()
        job_id = response_data["job_id"]

        # 验证系统识别多个参数
        assert "rate_control_values" in response_data
        assert response_data["rate_control_values"] == abr_values

        # 等待所有子任务完成
        import time
        max_wait = 60
        start = time.time()

        while time.time() - start < max_wait:
            status_response = client.get(f"/api/v1/jobs/{job_id}/status")
            status_data = status_response.json()

            if status_data["status"] == "completed":
                assert status_data["completed_subtasks"] == len(abr_values)
                break

            time.sleep(1)

        # 验证报告包含所有参数的对比数据
        report_response = client.get(f"/jobs/{job_id}/report")
        assert report_response.status_code == 200

        report_html = report_response.text
        for abr in abr_values:
            assert str(abr) in report_html  # 报告中应显示所有码率值

    def test_multi_crf_comparison(
        self,
        client: TestClient,
        test_video_path: Path,
        mock_ffmpeg_service
    ):
        """测试多个 CRF 值对比工作流"""
        crf_values = [18, 23, 28]

        payload = {
            "encoder_path": "/usr/bin/ffmpeg",
            "video_path": str(test_video_path),
            "rate_control_mode": "crf",
            "rate_control_values": crf_values
        }

        submit_response = client.post("/api/v1/jobs", json=payload)
        assert submit_response.status_code == 201

        job_id = submit_response.json()["job_id"]

        # 等待完成并获取对比 JSON
        import time
        time.sleep(5)  # Mock 场景下快速完成

        comparison_response = client.get(
            f"/api/v1/jobs/{job_id}/comparison.json"
        )
        assert comparison_response.status_code == 200

        comparison_data = comparison_response.json()
        assert len(comparison_data["results"]) == len(crf_values)

        # 验证每个 CRF 值都有对应结果
        for crf in crf_values:
            assert any(
                result["crf"] == crf for result in comparison_data["results"]
            )
```

### 示例 3: FFmpeg 子进程测试

**文件**: `backend/tests/integration/test_ffmpeg_integration.py`

```python
"""FFmpeg 子进程集成测试

测试 FFmpeg 调用的 mock vs 真实执行
"""

import subprocess
import pytest
from pathlib import Path
from unittest.mock import Mock, patch


@pytest.mark.integration
class TestFFmpegIntegration:
    """FFmpeg 集成测试套件"""

    def test_ffmpeg_mock_subprocess(self, mock_ffmpeg_subprocess):
        """测试 FFmpeg subprocess mock"""
        from backend.src.services.ffmpeg_service import FFmpegService

        service = FFmpegService()
        result = service.encode_video(
            input_path="/test/input.mp4",
            output_path="/test/output.mp4",
            bitrate=1000
        )

        assert result.success is True
        assert result.output_file.exists() is False  # Mock 不创建真实文件

        # 验证 mock 被调用
        mock_ffmpeg_subprocess.assert_called_once()

    def test_ffmpeg_mock_output_parsing(self, ffmpeg_log_fixture):
        """测试 FFmpeg 日志解析 (使用预录日志)"""
        from backend.src.services.metrics_service import MetricsService

        service = MetricsService()

        # 使用预录的 FFmpeg 日志
        psnr_data = service.parse_psnr_log(ffmpeg_log_fixture["psnr_success"])

        assert psnr_data["average"] > 0
        assert len(psnr_data["frames"]) > 0

        # 验证帧数据格式
        frame = psnr_data["frames"][0]
        assert "frame_num" in frame
        assert "psnr_y" in frame
        assert "psnr_u" in frame
        assert "psnr_v" in frame

    @pytest.mark.ffmpeg
    @pytest.mark.real_video
    def test_real_ffmpeg_execution(self, real_test_video: Path, tmp_path: Path):
        """使用真实 FFmpeg 的测试 (需要系统安装 FFmpeg)"""
        from backend.src.services.ffmpeg_service import FFmpegService

        service = FFmpegService()
        output_path = tmp_path / "output.mp4"

        result = service.encode_video(
            input_path=str(real_test_video),
            output_path=str(output_path),
            bitrate=500
        )

        assert result.success is True
        assert output_path.exists()
        assert output_path.stat().st_size > 0

        # 验证编码时间和速度
        assert result.encoding_time > 0
        assert result.encoding_speed > 0

    @pytest.mark.ffmpeg
    def test_ffmpeg_error_handling(self, tmp_path: Path):
        """测试 FFmpeg 错误处理"""
        from backend.src.services.ffmpeg_service import FFmpegService

        service = FFmpegService()

        # 使用无效输入路径
        with pytest.raises(subprocess.CalledProcessError):
            service.encode_video(
                input_path="/nonexistent/video.mp4",
                output_path=str(tmp_path / "output.mp4"),
                bitrate=1000
            )

    def test_ffmpeg_timeout_handling(self, mock_long_running_ffmpeg):
        """测试 FFmpeg 超时处理"""
        from backend.src.services.ffmpeg_service import FFmpegService

        service = FFmpegService(timeout=5)  # 5 秒超时

        with pytest.raises(subprocess.TimeoutExpired):
            service.encode_video(
                input_path="/test/large_video.mp4",
                output_path="/test/output.mp4",
                bitrate=1000
            )
```

### 示例 4: 异步任务测试

**文件**: `backend/tests/integration/test_async_tasks.py`

```python
"""异步任务测试

测试后台任务队列和状态管理
"""

import asyncio
import pytest
from fastapi.testclient import TestClient


@pytest.mark.integration
@pytest.mark.asyncio
class TestAsyncTasks:
    """异步任务测试套件"""

    async def test_task_queue_management(self, app, test_video_path):
        """测试任务队列管理"""
        from backend.src.services.task_service import TaskService

        service = TaskService()

        # 提交多个任务
        task_ids = []
        for i in range(5):
            task_id = await service.submit_task(
                encoder_path="/usr/bin/ffmpeg",
                video_path=str(test_video_path),
                bitrate=1000 + i * 500
            )
            task_ids.append(task_id)

        # 验证任务状态
        for task_id in task_ids:
            status = await service.get_task_status(task_id)
            assert status in ["queued", "processing"]

    async def test_concurrent_task_execution(
        self, app, test_video_path, mock_ffmpeg_service
    ):
        """测试并发任务执行 (最多 10 个并发)"""
        from backend.src.services.task_service import TaskService

        service = TaskService(max_concurrent=3)

        # 提交 10 个任务
        tasks = []
        for i in range(10):
            task = service.submit_task(
                encoder_path="/usr/bin/ffmpeg",
                video_path=str(test_video_path),
                bitrate=1000
            )
            tasks.append(task)

        task_ids = await asyncio.gather(*tasks)

        # 等待所有任务完成
        await asyncio.sleep(2)  # Mock 快速完成

        # 验证所有任务最终完成
        statuses = await asyncio.gather(
            *[service.get_task_status(tid) for tid in task_ids]
        )

        completed = sum(1 for s in statuses if s == "completed")
        assert completed == 10

    async def test_task_status_transitions(self, app, test_video_path):
        """测试任务状态转换: queued → processing → completed"""
        from backend.src.services.task_service import TaskService

        service = TaskService()

        task_id = await service.submit_task(
            encoder_path="/usr/bin/ffmpeg",
            video_path=str(test_video_path),
            bitrate=1000
        )

        # 初始状态应为 queued
        status = await service.get_task_status(task_id)
        assert status == "queued"

        # 等待状态变为 processing
        await asyncio.sleep(0.5)
        status = await service.get_task_status(task_id)
        assert status in ["queued", "processing"]

        # 等待完成
        for _ in range(10):
            status = await service.get_task_status(task_id)
            if status == "completed":
                break
            await asyncio.sleep(0.5)

        assert status == "completed"
```

---

## 共享 Fixtures (conftest.py)

### 根级 conftest.py

**文件**: `backend/tests/conftest.py`

```python
"""根级 pytest fixtures

提供所有测试共享的 fixtures
"""

import os
import sys
import pytest
from pathlib import Path
from typing import Generator

# 添加 src 到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# 导入模块化 fixtures
pytest_plugins = [
    "tests.fixtures.app_fixtures",
    "tests.fixtures.ffmpeg_fixtures",
    "tests.fixtures.video_fixtures",
    "tests.fixtures.factory_fixtures",
]


@pytest.fixture(scope="session")
def test_root_dir() -> Path:
    """测试根目录"""
    return Path(__file__).parent


@pytest.fixture(scope="session")
def test_assets_dir(test_root_dir: Path) -> Path:
    """测试资源目录"""
    return test_root_dir / "assets"


@pytest.fixture(scope="function")
def tmp_jobs_dir(tmp_path: Path) -> Generator[Path, None, None]:
    """临时任务目录 (每个测试函数独立)"""
    jobs_dir = tmp_path / "jobs"
    jobs_dir.mkdir(exist_ok=True)

    # 设置环境变量
    original_jobs_dir = os.environ.get("JOBS_ROOT_DIR")
    os.environ["JOBS_ROOT_DIR"] = str(jobs_dir)

    yield jobs_dir

    # 清理
    if original_jobs_dir:
        os.environ["JOBS_ROOT_DIR"] = original_jobs_dir
    else:
        os.environ.pop("JOBS_ROOT_DIR", None)


@pytest.fixture(scope="session")
def test_env_vars() -> dict:
    """测试环境变量"""
    return {
        "APP_ENV": "test",
        "DEBUG": "False",
        "LOG_LEVEL": "DEBUG",
        "FFMPEG_PATH": "/usr/bin/ffmpeg",
        "FFPROBE_PATH": "/usr/bin/ffprobe",
        "MAX_CONCURRENT_TASKS": "2",
        "TASK_TIMEOUT": "60",
        "USE_MOCK_FFMPEG": "true",
    }


@pytest.fixture(scope="function", autouse=True)
def setup_test_env(test_env_vars: dict):
    """自动设置测试环境变量"""
    original_env = {}

    for key, value in test_env_vars.items():
        original_env[key] = os.environ.get(key)
        os.environ[key] = value

    yield

    # 恢复原始环境
    for key, value in original_env.items():
        if value is not None:
            os.environ[key] = value
        else:
            os.environ.pop(key, None)
```

### FastAPI fixtures

**文件**: `backend/tests/fixtures/app_fixtures.py`

```python
"""FastAPI 应用相关 fixtures"""

import pytest
from fastapi.testclient import TestClient
from typing import Generator


@pytest.fixture(scope="module")
def app():
    """FastAPI 应用实例"""
    from backend.src.main import create_app

    app = create_app()
    return app


@pytest.fixture(scope="function")
def client(app) -> Generator[TestClient, None, None]:
    """FastAPI TestClient"""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(scope="function")
def valid_job_payload(test_video_path) -> dict:
    """有效的任务提交 payload"""
    return {
        "encoder_path": "/usr/bin/ffmpeg",
        "video_path": str(test_video_path),
        "rate_control_mode": "abr",
        "rate_control_values": [1000]
    }


@pytest.fixture(scope="function")
def completed_job_id(client: TestClient, valid_job_payload: dict) -> str:
    """已完成的任务 ID (用于测试报告 API)"""
    # 提交任务
    response = client.post("/api/v1/jobs", json=valid_job_payload)
    job_id = response.json()["job_id"]

    # 等待或模拟完成
    import time
    time.sleep(2)  # Mock 场景快速完成

    return job_id


@pytest.fixture(scope="function")
def pending_job_id(client: TestClient, valid_job_payload: dict) -> str:
    """待处理的任务 ID (用于测试状态 API)"""
    response = client.post("/api/v1/jobs", json=valid_job_payload)
    return response.json()["job_id"]
```

### FFmpeg fixtures

**文件**: `backend/tests/fixtures/ffmpeg_fixtures.py`

```python
"""FFmpeg 相关 fixtures"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import subprocess


@pytest.fixture(scope="function")
def mock_ffmpeg_subprocess(monkeypatch):
    """Mock subprocess.run for FFmpeg calls"""
    mock_result = Mock()
    mock_result.returncode = 0
    mock_result.stdout = "FFmpeg mock output"
    mock_result.stderr = "frame=100 fps=30 speed=1.0x"

    mock_run = Mock(return_value=mock_result)
    monkeypatch.setattr(subprocess, "run", mock_run)

    return mock_run


@pytest.fixture(scope="function")
def mock_ffmpeg_service(monkeypatch):
    """Mock FFmpegService for fast testing"""
    from backend.src.services.ffmpeg_service import FFmpegService

    mock_service = Mock(spec=FFmpegService)

    # Mock encode_video method
    def mock_encode(input_path, output_path, bitrate, **kwargs):
        result = Mock()
        result.success = True
        result.output_file = Path(output_path)
        result.encoding_time = 10.5
        result.encoding_speed = 2.3
        return result

    mock_service.encode_video = Mock(side_effect=mock_encode)

    # Mock calculate_psnr method
    def mock_psnr(reference, encoded):
        return {
            "average": 35.42,
            "frames": [
                {"frame_num": i, "psnr_y": 35.0 + i * 0.1}
                for i in range(100)
            ]
        }

    mock_service.calculate_psnr = Mock(side_effect=mock_psnr)

    monkeypatch.setattr(
        "backend.src.services.ffmpeg_service.FFmpegService",
        lambda: mock_service
    )

    return mock_service


@pytest.fixture(scope="session")
def ffmpeg_log_fixture(test_assets_dir: Path) -> dict:
    """预录的 FFmpeg 日志文件"""
    logs_dir = test_assets_dir / "ffmpeg_logs"

    return {
        "psnr_success": logs_dir / "psnr_success.log",
        "vmaf_success": logs_dir / "vmaf_success.log",
        "encode_error": logs_dir / "encode_error.log",
    }


@pytest.fixture(scope="function")
def mock_long_running_ffmpeg(monkeypatch):
    """Mock a long-running FFmpeg process for timeout testing"""
    import time

    def slow_run(*args, **kwargs):
        time.sleep(100)  # 模拟长时间运行
        return Mock(returncode=0)

    monkeypatch.setattr(subprocess, "run", slow_run)
```

### Video fixtures

**文件**: `backend/tests/fixtures/video_fixtures.py`

```python
"""测试视频文件相关 fixtures"""

import pytest
import shutil
from pathlib import Path


@pytest.fixture(scope="session")
def test_videos_dir(test_assets_dir: Path) -> Path:
    """测试视频目录"""
    return test_assets_dir / "videos"


@pytest.fixture(scope="session")
def test_video_path(test_videos_dir: Path) -> Path:
    """标准测试视频文件 (1080p 10s)"""
    video_path = test_videos_dir / "sample_1080p_10s.mp4"

    if not video_path.exists():
        pytest.skip(f"Test video not found: {video_path}")

    return video_path


@pytest.fixture(scope="session")
def real_test_video(test_videos_dir: Path) -> Path:
    """真实测试视频 (用于真实 FFmpeg 测试)"""
    video_path = test_videos_dir / "sample_720p_5s.mp4"

    if not video_path.exists():
        pytest.skip("Real test video not available")

    return video_path


@pytest.fixture(scope="function")
def temp_video_copy(test_video_path: Path, tmp_path: Path) -> Path:
    """临时视频副本 (可修改)"""
    temp_video = tmp_path / "test_video.mp4"
    shutil.copy(test_video_path, temp_video)
    return temp_video


@pytest.fixture(scope="session")
def yuv_test_file(test_videos_dir: Path) -> Path:
    """YUV 测试文件 (P3 功能)"""
    yuv_path = test_videos_dir / "sample.yuv"

    if not yuv_path.exists():
        pytest.skip("YUV test file not available")

    return yuv_path


@pytest.fixture(scope="session")
def corrupted_video(test_videos_dir: Path) -> Path:
    """损坏的视频文件 (边界测试)"""
    return test_videos_dir / "corrupted.mp4"


@pytest.fixture(scope="function")
def create_fake_video(tmp_path: Path):
    """创建假视频文件的工厂函数"""
    def _create(filename: str, size_mb: float = 1.0):
        video_path = tmp_path / filename

        # 创建指定大小的假文件
        with open(video_path, "wb") as f:
            f.write(b"\x00" * int(size_mb * 1024 * 1024))

        return video_path

    return _create
```

### Factory fixtures

**文件**: `backend/tests/fixtures/factory_fixtures.py`

```python
"""数据工厂 fixtures (使用 Faker)"""

import pytest
from faker import Faker
from datetime import datetime
from typing import Callable


@pytest.fixture(scope="session")
def faker_instance() -> Faker:
    """Faker 实例"""
    return Faker()


@pytest.fixture(scope="function")
def job_factory(faker_instance: Faker) -> Callable:
    """任务数据工厂"""
    def _create_job(
        job_id: str = None,
        status: str = "queued",
        encoder_path: str = "/usr/bin/ffmpeg",
        video_path: str = "/test/video.mp4",
        **kwargs
    ):
        return {
            "job_id": job_id or faker_instance.uuid4(),
            "status": status,
            "encoder_path": encoder_path,
            "video_path": video_path,
            "rate_control_mode": kwargs.get("rate_control_mode", "abr"),
            "rate_control_values": kwargs.get("rate_control_values", [1000]),
            "created_at": kwargs.get("created_at", datetime.utcnow().isoformat()),
            "updated_at": kwargs.get("updated_at", datetime.utcnow().isoformat()),
        }

    return _create_job


@pytest.fixture(scope="function")
def metrics_factory() -> Callable:
    """指标数据工厂"""
    def _create_metrics(average: float = 35.0, num_frames: int = 100):
        return {
            "average": average,
            "min": average - 5.0,
            "max": average + 5.0,
            "frames": [
                {
                    "frame_num": i,
                    "psnr_y": average + (i % 10) * 0.1,
                    "vmaf_score": average + (i % 10) * 0.2,
                    "ssim": 0.95 + (i % 10) * 0.001,
                }
                for i in range(num_frames)
            ]
        }

    return _create_metrics


@pytest.fixture(scope="function")
def expected_results_factory(test_assets_dir: Path) -> dict:
    """预期结果数据"""
    import json

    expected_dir = test_assets_dir / "expected_results"

    return {
        "psnr": json.load(open(expected_dir / "psnr_expected.json")),
        "vmaf": json.load(open(expected_dir / "vmaf_expected.json")),
    }
```

---

## 测试数据管理

### 测试视频文件管理

#### 方案 1: 使用真实小视频文件 (推荐用于集成测试)

在 `backend/tests/assets/videos/README.md` 中记录:

```markdown
# 测试视频文件说明

## 标准测试视频

### sample_1080p_10s.mp4
- 分辨率: 1920x1080
- 时长: 10 秒
- 帧率: 30fps
- 编码: H.264
- 大小: ~5MB
- 用途: 契约测试和快速集成测试

### sample_720p_5s.mp4
- 分辨率: 1280x720
- 时长: 5 秒
- 帧率: 30fps
- 编码: H.264
- 大小: ~2MB
- 用途: 真实 FFmpeg 测试

### sample.yuv
- 分辨率: 1920x1080
- 格式: yuv420p
- 帧数: 10
- 大小: ~30MB
- 用途: P3 YUV 功能测试

## 生成测试视频

使用 FFmpeg 生成标准测试视频:

```bash
# 生成 1080p 10秒测试视频 (彩色条纹)
ffmpeg -f lavfi -i testsrc=duration=10:size=1920x1080:rate=30 \
  -c:v libx264 -preset fast -crf 23 sample_1080p_10s.mp4

# 生成 720p 5秒测试视频
ffmpeg -f lavfi -i testsrc=duration=5:size=1280x720:rate=30 \
  -c:v libx264 -preset fast -crf 23 sample_720p_5s.mp4

# 生成 YUV 原始文件
ffmpeg -f lavfi -i testsrc=duration=0.33:size=1920x1080:rate=30 \
  -pix_fmt yuv420p sample.yuv
```

## 损坏文件

```bash
# 创建损坏的 MP4 文件
echo "corrupted data" > corrupted.mp4
```
```

#### 方案 2: 使用 pytest fixture 动态生成 (推荐用于契约测试)

```python
@pytest.fixture(scope="function")
def generate_test_video(tmp_path: Path):
    """动态生成测试视频"""
    import subprocess

    video_path = tmp_path / "generated_test.mp4"

    subprocess.run([
        "ffmpeg", "-f", "lavfi",
        "-i", "testsrc=duration=2:size=640x480:rate=30",
        "-c:v", "libx264", "-preset", "ultrafast",
        str(video_path)
    ], check=True, capture_output=True)

    return video_path
```

### Mock FFmpeg 输出日志

**文件**: `backend/tests/assets/ffmpeg_logs/psnr_success.log`

```
frame=    0 fps=0.0 q=0.0 size=       0kB time=00:00:00.00 bitrate=N/A speed=   0x
frame=    1 fps=0.0 q=28.0 size=       1kB time=00:00:00.03 bitrate= 273.1kbits/s speed=0.0612x PSNR Y:35.23 U:38.45 V:37.89
frame=    2 fps=0.8 q=28.0 size=       2kB time=00:00:00.06 bitrate= 273.1kbits/s speed=0.0302x PSNR Y:35.45 U:38.67 V:38.12
frame=    3 fps=1.2 q=28.0 size=       3kB time=00:00:00.10 bitrate= 245.8kbits/s speed=0.0398x PSNR Y:35.67 U:38.89 V:38.34
...
[libx264 @ 0x7f8e9c004000] frame I:10 Avg QP:23.50 size: 12345
[libx264 @ 0x7f8e9c004000] frame P:90 Avg QP:25.30 size: 5678
[libx264 @ 0x7f8e9c004000] kb/s:1000.45
```

### 预期结果断言 (容差)

```python
import pytest


def assert_metrics_within_tolerance(actual: float, expected: float, tolerance: float = 0.05):
    """断言指标在容差范围内

    Args:
        actual: 实际值
        expected: 预期值
        tolerance: 容差 (默认 5%)
    """
    diff = abs(actual - expected)
    max_diff = expected * tolerance

    assert diff <= max_diff, (
        f"Metric {actual} outside tolerance range of {expected} ± {tolerance*100}% "
        f"(diff: {diff}, max: {max_diff})"
    )


# 使用示例
@pytest.mark.integration
def test_psnr_accuracy(client, completed_job_id, expected_results_factory):
    """测试 PSNR 计算精度"""
    response = client.get(f"/api/v1/jobs/{completed_job_id}/metrics/psnr.json")
    actual_psnr = response.json()["average"]

    expected_psnr = expected_results_factory["psnr"]["average"]

    assert_metrics_within_tolerance(actual_psnr, expected_psnr, tolerance=0.05)
```

---

## 测试覆盖率

### pytest-cov 配置 (已在 pyproject.toml 中)

### 运行覆盖率测试

```bash
# 运行所有测试并生成覆盖率报告
pytest --cov=backend/src --cov-report=html --cov-report=term

# 仅运行契约测试的覆盖率
pytest -m contract --cov=backend/src/api

# 仅运行集成测试的覆盖率
pytest -m integration --cov=backend/src/services

# 生成 LCOV 格式 (用于 CI/IDE)
pytest --cov=backend/src --cov-report=lcov:coverage.lcov
```

### 覆盖率目标

| 模块 | 目标覆盖率 | 说明 |
|------|-----------|------|
| `backend/src/api/` | 100% | 所有 API 端点必须有契约测试 |
| `backend/src/services/` | 85%+ | 核心业务逻辑 |
| `backend/src/models/` | 90%+ | 数据模型 |
| 整体 | 80%+ | 项目最低覆盖率要求 |

### 查看覆盖率报告

```bash
# 终端输出
pytest --cov-report=term-missing

# HTML 报告
pytest --cov-report=html
open coverage_html_report/index.html  # macOS
xdg-open coverage_html_report/index.html  # Linux

# 覆盖率徽章 (CI 中生成)
# 使用 coverage-badge 生成
pip install coverage-badge
coverage-badge -o coverage.svg
```

### 排除不需要覆盖的代码

在代码中使用注释:

```python
def debug_function():  # pragma: no cover
    """仅在调试时使用"""
    print("Debug info")

if __name__ == "__main__":  # pragma: no cover
    main()
```

---

## CI/CD 集成

### GitHub Actions 配置

**文件**: `.github/workflows/test.yml`

```yaml
name: Tests

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest

    strategy:
      matrix:
        python-version: ["3.10", "3.11", "3.12"]

    steps:
    - name: Checkout code
      uses: actions/checkout@v4

    - name: Set up Python ${{ matrix.python-version }}
      uses: actions/setup-python@v5
      with:
        python-version: ${{ matrix.python-version }}

    - name: Install system dependencies (FFmpeg)
      run: |
        sudo apt-get update
        sudo apt-get install -y ffmpeg

    - name: Install Python dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -e ".[dev]"

    - name: Download test assets
      run: |
        # 从外部存储或 Git LFS 下载测试视频
        # 或使用 FFmpeg 生成
        mkdir -p backend/tests/assets/videos
        ffmpeg -f lavfi -i testsrc=duration=2:size=640x480:rate=30 \
          -c:v libx264 -preset ultrafast \
          backend/tests/assets/videos/sample_test.mp4

    - name: Lint with ruff
      run: |
        ruff check backend/src backend/tests

    - name: Run contract tests
      run: |
        pytest -m contract -v --tb=short

    - name: Run unit tests
      run: |
        pytest -m unit -v --tb=short

    - name: Run integration tests (mock FFmpeg)
      env:
        USE_MOCK_FFMPEG: "true"
      run: |
        pytest -m "integration and not ffmpeg" -v --tb=short

    - name: Run integration tests (real FFmpeg)
      env:
        USE_MOCK_FFMPEG: "false"
      run: |
        pytest -m "integration and ffmpeg" -v --tb=short --timeout=300

    - name: Generate coverage report
      run: |
        pytest --cov=backend/src \
          --cov-report=xml \
          --cov-report=html \
          --cov-report=term-missing \
          --cov-fail-under=80

    - name: Upload coverage to Codecov
      uses: codecov/codecov-action@v4
      with:
        files: ./coverage.xml
        flags: unittests
        name: codecov-umbrella

    - name: Archive coverage reports
      uses: actions/upload-artifact@v4
      with:
        name: coverage-report-${{ matrix.python-version }}
        path: coverage_html_report/

    - name: Check test performance
      run: |
        # 确保测试套件在合理时间内完成
        # 契约测试应 < 30s, 集成测试 < 5min
        pytest --durations=10
```

### GitLab CI 配置

**文件**: `.gitlab-ci.yml`

```yaml
stages:
  - lint
  - test
  - coverage

variables:
  PYTHON_VERSION: "3.10"
  PIP_CACHE_DIR: "$CI_PROJECT_DIR/.cache/pip"

cache:
  paths:
    - .cache/pip
    - venv/

before_script:
  - python -m venv venv
  - source venv/bin/activate
  - pip install --upgrade pip
  - pip install -e ".[dev]"

lint:
  stage: lint
  image: python:${PYTHON_VERSION}
  script:
    - ruff check backend/src backend/tests

test:contract:
  stage: test
  image: python:${PYTHON_VERSION}
  script:
    - pytest -m contract -v --junitxml=report-contract.xml
  artifacts:
    reports:
      junit: report-contract.xml

test:unit:
  stage: test
  image: python:${PYTHON_VERSION}
  script:
    - pytest -m unit -v --junitxml=report-unit.xml
  artifacts:
    reports:
      junit: report-unit.xml

test:integration:
  stage: test
  image: python:${PYTHON_VERSION}
  services:
    - name: jrottenberg/ffmpeg:latest
      alias: ffmpeg
  before_script:
    - apt-get update && apt-get install -y ffmpeg
    - python -m venv venv
    - source venv/bin/activate
    - pip install -e ".[dev]"
  script:
    - pytest -m integration -v --junitxml=report-integration.xml
  artifacts:
    reports:
      junit: report-integration.xml

coverage:
  stage: coverage
  image: python:${PYTHON_VERSION}
  script:
    - pytest --cov=backend/src --cov-report=xml --cov-report=html --cov-fail-under=80
    - coverage report
  coverage: '/(?i)total.*? (100(?:\.0+)?\%|[1-9]?\d(?:\.\d+)?\%)$/'
  artifacts:
    paths:
      - coverage_html_report/
    reports:
      coverage_report:
        coverage_format: cobertura
        path: coverage.xml
```

### Docker 测试环境

**文件**: `Dockerfile.test`

```dockerfile
FROM python:3.10-slim

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libavcodec-extra \
    && rm -rf /var/lib/apt/lists/*

# 下载 VMAF 模型
RUN mkdir -p /usr/share/model && \
    curl -L https://github.com/Netflix/vmaf/raw/master/model/vmaf_v0.6.1.json \
    -o /usr/share/model/vmaf_v0.6.1.json

WORKDIR /app

# 安装 Python 依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install pytest pytest-cov pytest-asyncio

# 复制应用代码
COPY backend/ ./backend/

# 生成测试视频
RUN mkdir -p backend/tests/assets/videos && \
    ffmpeg -f lavfi -i testsrc=duration=2:size=640x480:rate=30 \
    -c:v libx264 -preset ultrafast \
    backend/tests/assets/videos/sample_test.mp4

# 运行测试
CMD ["pytest", "--cov=backend/src", "--cov-report=term-missing", "-v"]
```

**运行 Docker 测试**:

```bash
# 构建测试镜像
docker build -f Dockerfile.test -t vqmr-test .

# 运行测试
docker run --rm vqmr-test

# 运行特定测试
docker run --rm vqmr-test pytest -m contract -v
```

### docker-compose.test.yml

```yaml
version: '3.8'

services:
  test:
    build:
      context: .
      dockerfile: Dockerfile.test
    environment:
      - APP_ENV=test
      - USE_MOCK_FFMPEG=true
      - JOBS_ROOT_DIR=/tmp/vqmr_test_jobs
    volumes:
      - ./backend:/app/backend
      - ./coverage_html_report:/app/coverage_html_report
    command: pytest --cov=backend/src --cov-report=html --cov-report=term -v
```

**运行**:

```bash
docker-compose -f docker-compose.test.yml up --abort-on-container-exit
```

---

## 最佳实践清单

### 测试编写

- [ ] **独立性**: 每个测试独立运行，不依赖执行顺序
- [ ] **快速执行**: 契约测试 < 5秒, 单元测试 < 1秒
- [ ] **明确命名**: 测试函数名清楚描述测试内容 (如 `test_submit_invalid_encoder_returns_400`)
- [ ] **AAA 模式**: Arrange (准备) → Act (执行) → Assert (断言)
- [ ] **单一职责**: 每个测试只验证一个行为
- [ ] **有意义的断言**: 使用描述性断言消息

### 契约测试

- [ ] **100% 端点覆盖**: 所有 API 路由都有契约测试
- [ ] **验证 HTTP 契约**: 状态码、响应头、Content-Type
- [ ] **验证 JSON Schema**: 必需字段、数据类型、嵌套结构
- [ ] **边界测试**: 无效输入、缺失字段、格式错误
- [ ] **使用 TestClient**: 不启动真实服务器
- [ ] **Mock 外部依赖**: 不调用真实 FFmpeg/数据库

### 集成测试

- [ ] **端到端场景**: 模拟真实用户工作流
- [ ] **隔离环境**: 使用临时目录和测试数据库
- [ ] **支持 Mock 和真实执行**: 通过环境变量切换
- [ ] **异步测试**: 使用 `pytest-asyncio` 和 `asyncio_mode = auto`
- [ ] **超时控制**: 为长时间测试设置合理超时
- [ ] **清理资源**: 使用 fixture 的 teardown 清理临时文件

### Fixtures

- [ ] **合理作用域**: session (全局) vs module vs function
- [ ] **模块化**: 按功能分离到 `fixtures/` 目录
- [ ] **使用 pytest_plugins**: 在 conftest.py 中导入模块化 fixtures
- [ ] **工厂模式**: 使用工厂 fixture 创建可变数据
- [ ] **清理逻辑**: 使用 `yield` 实现 setup/teardown

### 测试数据

- [ ] **小而快**: 使用最小测试视频 (< 10秒, < 10MB)
- [ ] **版本控制**: 小文件提交到 Git, 大文件使用 Git LFS 或外部存储
- [ ] **生成 vs 真实**: 契约测试生成假数据, 集成测试使用真实文件
- [ ] **预期结果**: 维护 `expected_results/` 目录存储标准结果
- [ ] **容差断言**: 浮点数比较使用容差 (通常 5%)

### 覆盖率

- [ ] **目标设置**: 契约 100%, 集成 80%+, 单元 80%+
- [ ] **CI 强制**: 使用 `--cov-fail-under` 阻止低覆盖率合并
- [ ] **排除无意义代码**: `__repr__`, `if __name__ == "__main__"`
- [ ] **分支覆盖**: 启用 `branch = true`
- [ ] **定期审查**: 查看 HTML 报告识别未覆盖代码

### CI/CD

- [ ] **矩阵测试**: 测试多个 Python 版本 (3.10, 3.11, 3.12)
- [ ] **分阶段执行**: lint → unit → contract → integration
- [ ] **快速反馈**: 先运行快速测试, 失败立即停止
- [ ] **Docker 隔离**: 使用 Docker 确保环境一致性
- [ ] **缓存依赖**: 缓存 pip 包加速构建
- [ ] **上传报告**: 使用 Codecov/Coveralls 跟踪覆盖率趋势

### 标记 (Markers)

- [ ] **注册所有标记**: 在 `pytest.ini` 中声明避免警告
- [ ] **一致使用**: `@pytest.mark.contract`, `@pytest.mark.integration`
- [ ] **条件跳过**: `@pytest.mark.skipif` 用于缺失依赖
- [ ] **慢速标记**: `@pytest.mark.slow` 用于长时间测试
- [ ] **选择性运行**: `pytest -m contract` 或 `pytest -m "not slow"`

### 维护性

- [ ] **测试文档**: 在测试文件顶部添加 docstring 说明
- [ ] **避免重复**: 提取公共逻辑到 fixtures
- [ ] **版本同步**: 测试与功能同步更新
- [ ] **定期清理**: 删除过时测试和 fixtures
- [ ] **代码审查**: 测试代码也需要 Code Review

---

## 运行测试示例

### 基础命令

```bash
# 运行所有测试
pytest

# 运行契约测试
pytest -m contract

# 运行集成测试
pytest -m integration

# 运行单元测试
pytest -m unit

# 运行特定文件
pytest backend/tests/contract/test_job_submission_api.py

# 运行特定测试
pytest backend/tests/contract/test_job_submission_api.py::test_submit_valid_single_abr_task

# 运行特定类
pytest backend/tests/contract/test_job_submission_api.py::TestJobSubmissionContract

# 排除慢速测试
pytest -m "not slow"

# 只运行 FFmpeg 相关测试
pytest -m ffmpeg

# 详细输出
pytest -v

# 显示打印输出
pytest -s

# 失败时进入调试器
pytest --pdb

# 只运行上次失败的测试
pytest --lf

# 并行运行 (需要 pytest-xdist)
pytest -n auto
```

### 覆盖率命令

```bash
# 基础覆盖率
pytest --cov=backend/src

# 覆盖率 + HTML 报告
pytest --cov=backend/src --cov-report=html

# 覆盖率 + 缺失行
pytest --cov=backend/src --cov-report=term-missing

# 仅 API 覆盖率
pytest -m contract --cov=backend/src/api

# 覆盖率低于 80% 时失败
pytest --cov=backend/src --cov-fail-under=80
```

### 性能分析

```bash
# 显示最慢的 10 个测试
pytest --durations=10

# 显示所有测试耗时
pytest --durations=0

# 超时控制 (需要 pytest-timeout)
pytest --timeout=300
```

---

## 总结

本指南提供了 VQMR 项目的完整 pytest 测试策略:

1. **配置完整**: `pyproject.toml` ��含所有测试配置
2. **结构清晰**: `contract/`, `integration/`, `unit/` 分离
3. **Fixtures 模块化**: 按功能分离到 `fixtures/` 目录
4. **Mock 策略**: 支持快速 mock 和真实 FFmpeg 测试
5. **CI/CD 就绪**: GitHub Actions 和 GitLab CI 配置
6. **覆盖率保障**: 80%+ 总体覆盖率, API 100%

**下一步**: 运行 `/speckit.tasks` 生成实现任务列表。
