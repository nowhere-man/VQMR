# API 契约规范：视频质量指标报告系统

**特性分支**: `001-video-quality-metrics-report`
**设计日期**: 2025-10-25
**API 版本**: v1
**状态**: Phase 1 设计

## 概述

本文档定义 VQMR 项目的 HTTP API 契约，基于功能需求（spec.md）和数据模型（data-model.md）。所有端点使用 REST 架构，遵循标准 HTTP 方法语义。

## 一、端点总览

| 端点 | 方法 | 描述 | 优先级 | 来源需求 |
|------|------|------|--------|---------|
| `/` | GET | 上传页面（HTML） | P1 | FR-001 |
| `/jobs` | POST | 创建编码任务 | P1 | FR-013, FR-029 |
| `/jobs/{job_id}` | GET | 任务详情/报告页（HTML） | P1 | FR-022, FR-023, FR-029 |
| `/jobs/{job_id}/status` | GET | 任务状态（JSON） | P1 | FR-029 |
| `/jobs/{job_id}/psnr.json` | GET | 质量指标（JSON） | P1 | FR-026 |
| `/jobs/{job_id}/psnr.csv` | GET | 质量指标（CSV 下载） | P2 | FR-026 |
| `/health` | GET | 健康检查 | P1 | - |

---

## 二、端点详细规范

### 2.1 GET / - 上传页面

**描述**: 返回任务提交表单（单/双文件模式切换）

**请求**:

```
GET / HTTP/1.1
Host: localhost:8080
Accept: text/html
```

**响应**:

```
HTTP/1.1 200 OK
Content-Type: text/html; charset=utf-8

<!DOCTYPE html>
<html>
<head>
    <title>VQMR - 视频质量指标报告</title>
    <!-- Tailwind CSS CDN -->
</head>
<body>
    <!-- 上传表单 -->
</body>
</html>
```

**状态码**:
- `200 OK`: 成功返回页面

**契约测试**:

```python
def test_upload_page(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "VQMR" in response.text
```

---

### 2.2 POST /jobs - 创建编码任务

**描述**: 提交编码任务，验证输入后加入队列，返回 303 重定向

**请求**:

```
POST /jobs HTTP/1.1
Host: localhost:8080
Content-Type: multipart/form-data; boundary=----WebKitFormBoundary

------WebKitFormBoundary
Content-Disposition: form-data; name="encoder_path"

/usr/bin/x264
------WebKitFormBoundary
Content-Disposition: form-data; name="video_file"; filename="test.mp4"
Content-Type: video/mp4

[二进制视频数据]
------WebKitFormBoundary
Content-Disposition: form-data; name="rate_control"

abr
------WebKitFormBoundary
Content-Disposition: form-data; name="rate_values"

500,1000,2000
------WebKitFormBoundary--
```

**请求参数**:

| 参数 | 类型 | 必需 | 描述 | 验证规则 | 来源需求 |
|------|------|------|------|---------|---------|
| `encoder_path` | `string` | ✅ | 编码器路径 | 文件存在且可执行 | FR-002, FR-003 |
| `video_file` | `file` | ✅ | 上传的视频文件 | 大小 < 10GB, 类型: video/* | FR-004, FR-007 |
| `rate_control` | `string` | ✅ | 码控模式 | `abr` 或 `crf` | FR-008, FR-009, FR-012 |
| `rate_values` | `string` | ✅ | 码控参数值（逗号分隔） | 1-10 个值，范围有效 | FR-010, FR-011 |
| `video_format` | `string` | ❌ | 视频格式 | `container` 或 `raw_yuv`（默认 `container`） | FR-005, FR-006 |
| `yuv_resolution` | `string` | ❌ | YUV 分辨率 | 格式: `1920x1080`（YUV 必需） | FR-006 |
| `yuv_pixel_format` | `string` | ❌ | YUV 像素格式 | 如 `yuv420p`（YUV 必需） | FR-006 |
| `yuv_frame_rate` | `float` | ❌ | YUV 帧率 | 1-240 fps（YUV 必需） | FR-006 |

**响应（成功）**:

```
HTTP/1.1 303 See Other
Location: /jobs/abc123def456
Content-Type: application/json

{
  "job_id": "abc123def456",
  "status": "queued",
  "created_at": "2025-10-25T10:30:00Z",
  "message": "任务已创建，正在处理中"
}
```

**响应（验证失败）**:

```
HTTP/1.1 422 Unprocessable Entity
Content-Type: application/json

{
  "detail": [
    {
      "loc": ["body", "encoder_path"],
      "msg": "编码器文件不存在: /usr/bin/x264",
      "type": "value_error"
    }
  ]
}
```

**状态码**:
- `303 See Other`: 任务创建成功，重定向到任务详情页
- `422 Unprocessable Entity`: 验证失败（路径不存在、参数无效）
- `413 Payload Too Large`: 文件过大
- `500 Internal Server Error`: 服务器错误

**契约测试**:

```python
def test_create_job_success(client, test_video_file):
    response = client.post("/jobs", data={
        "encoder_path": "/usr/bin/x264",
        "rate_control": "abr",
        "rate_values": "1000"
    }, files={"video_file": test_video_file})

    assert response.status_code == 303
    assert "Location" in response.headers
    assert "/jobs/" in response.headers["Location"]

    json_data = response.json()
    assert "job_id" in json_data
    assert json_data["status"] == "queued"

def test_create_job_invalid_encoder(client, test_video_file):
    response = client.post("/jobs", data={
        "encoder_path": "/nonexistent/encoder",
        "rate_control": "abr",
        "rate_values": "1000"
    }, files={"video_file": test_video_file})

    assert response.status_code == 422
    assert "编码器文件不存在" in response.json()["detail"][0]["msg"]
```

---

### 2.3 GET /jobs/{job_id} - 任务详情/报告页

**描述**: 返回任务状态和可视化报告（HTML）

**请求**:

```
GET /jobs/abc123def456 HTTP/1.1
Host: localhost:8080
Accept: text/html
```

**响应（处理中）**:

```
HTTP/1.1 200 OK
Content-Type: text/html

<!-- 报告页包含：
- 任务状态：processing
- 进度条：2/3 已完成
- 已完成参数的部分报告
- 自动刷新脚本（AJAX 轮询）
-->
```

**响应（已完成）**:

```
HTTP/1.1 200 OK
Content-Type: text/html

<!-- 完整报告页包含：
- 视频元数据（分辨率/帧率/编解码器）
- 总体指标摘要（PSNR/VMAF/SSIM 平均值）
- Chart.js 逐帧曲线图
- 性能指标柱状图
- CSV 下载按钮
-->
```

**响应（失败）**:

```
HTTP/1.1 200 OK
Content-Type: text/html

<!-- 错误页包含：
- 任务状态：failed
- 错误消息（详细说明）
- 日志下载链接
-->
```

**状态码**:
- `200 OK`: 成功返回页面
- `404 Not Found`: 任务 ID 不存在

**契约测试**:

```python
def test_job_report_completed(client, completed_job_id):
    response = client.get(f"/jobs/{completed_job_id}")
    assert response.status_code == 200
    assert "Chart.js" in response.text
    assert "PSNR" in response.text
    assert "VMAF" in response.text

def test_job_report_not_found(client):
    response = client.get("/jobs/nonexistent_job_id")
    assert response.status_code == 404
```

---

### 2.4 GET /jobs/{job_id}/status - 任务状态（JSON）

**描述**: 返回任务当前状态和进度（用于 AJAX 轮询）

**请求**:

```
GET /jobs/abc123def456/status HTTP/1.1
Host: localhost:8080
Accept: application/json
```

**响应（处理中）**:

```json
{
  "job_id": "abc123def456",
  "status": "processing",
  "progress": {
    "current_rate_param": 1000,
    "completed_params": [500],
    "total_tasks": 3,
    "completed_tasks": 1,
    "progress_percent": 33.33
  },
  "updated_at": "2025-10-25T10:35:00Z"
}
```

**响应（已完成）**:

```json
{
  "job_id": "abc123def456",
  "status": "completed",
  "progress": {
    "current_rate_param": null,
    "completed_params": [500, 1000, 2000],
    "total_tasks": 3,
    "completed_tasks": 3,
    "progress_percent": 100.0
  },
  "updated_at": "2025-10-25T10:45:00Z"
}
```

**响应（失败）**:

```json
{
  "job_id": "abc123def456",
  "status": "failed",
  "error": "编码器崩溃: /usr/bin/x264 返回码 139 (段错误)",
  "updated_at": "2025-10-25T10:40:00Z"
}
```

**状态码**:
- `200 OK`: 成功返回状态
- `404 Not Found`: 任务 ID 不存在

**契约测试**:

```python
def test_job_status_processing(client, processing_job_id):
    response = client.get(f"/jobs/{processing_job_id}/status")
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "processing"
    assert "progress" in data
    assert data["progress"]["total_tasks"] > 0

def test_job_status_completed(client, completed_job_id):
    response = client.get(f"/jobs/{completed_job_id}/status")
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "completed"
    assert data["progress"]["progress_percent"] == 100.0
```

---

### 2.5 GET /jobs/{job_id}/psnr.json - 质量指标（JSON）

**描述**: 返回完整质量指标数据（程序化访问）

**请求**:

```
GET /jobs/abc123def456/psnr.json HTTP/1.1
Host: localhost:8080
Accept: application/json
```

**响应**:

```json
{
  "job_id": "abc123def456",
  "video_metadata": {
    "resolution": "1920x1080",
    "frame_rate": 30.0,
    "codec": "h264",
    "duration": 10.5
  },
  "results": [
    {
      "rate_control_param": 500,
      "quality_metrics": {
        "psnr_y": 38.45,
        "psnr_u": 42.12,
        "psnr_v": 41.87,
        "psnr_avg": 40.81,
        "vmaf": 72.34,
        "ssim": 0.9456,
        "actual_bitrate": 487,
        "frames": [
          {"frame_number": 1, "psnr_y": 39.2, "vmaf": 73.5, "ssim": 0.948},
          {"frame_number": 2, "psnr_y": 37.8, "vmaf": 71.3, "ssim": 0.943}
        ]
      },
      "performance_metrics": {
        "encoding_time": 12.5,
        "encoding_speed": 25.2,
        "cpu_utilization": 85.3,
        "frame_latency": {
          "avg_ms": 40.5,
          "min_ms": 25.3,
          "max_ms": 75.8
        }
      }
    },
    {
      "rate_control_param": 1000,
      "quality_metrics": { "...": "..." },
      "performance_metrics": { "...": "..." }
    }
  ],
  "created_at": "2025-10-25T10:45:00Z"
}
```

**状态码**:
- `200 OK`: 成功返回数据
- `404 Not Found`: 任务 ID 不存在
- `409 Conflict`: 任务未完成（状态不是 `completed`）

**契约测试**:

```python
def test_psnr_json_completed(client, completed_job_id):
    response = client.get(f"/jobs/{completed_job_id}/psnr.json")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/json"

    data = response.json()
    assert "video_metadata" in data
    assert "results" in data
    assert len(data["results"]) > 0

    # 验证数据结构
    result = data["results"][0]
    assert "quality_metrics" in result
    assert "performance_metrics" in result

    metrics = result["quality_metrics"]
    assert "psnr_y" in metrics
    assert "vmaf" in metrics
    assert 0 <= metrics["vmaf"] <= 100
    assert 0 <= metrics["ssim"] <= 1

def test_psnr_json_not_completed(client, processing_job_id):
    response = client.get(f"/jobs/{processing_job_id}/psnr.json")
    assert response.status_code == 409
    assert "未完成" in response.json()["detail"]
```

---

### 2.6 GET /jobs/{job_id}/psnr.csv - 质量指标（CSV 下载）

**描述**: 导出逐帧质量指标为 CSV 格式

**请求**:

```
GET /jobs/abc123def456/psnr.csv HTTP/1.1
Host: localhost:8080
Accept: text/csv
```

**响应**:

```
HTTP/1.1 200 OK
Content-Type: text/csv; charset=utf-8
Content-Disposition: attachment; filename="abc123def456_metrics.csv"

rate_control_param,frame_number,psnr_y,psnr_u,psnr_v,vmaf,ssim
500,1,39.2,42.5,41.8,73.5,0.948
500,2,37.8,41.3,40.9,71.3,0.943
1000,1,42.3,45.2,44.7,85.6,0.975
1000,2,41.1,44.0,43.5,83.4,0.968
```

**状态码**:
- `200 OK`: 成功返回 CSV
- `404 Not Found`: 任务 ID 不存在
- `409 Conflict`: 任务未完成

**契约测试**:

```python
def test_psnr_csv_download(client, completed_job_id):
    response = client.get(f"/jobs/{completed_job_id}/psnr.csv")
    assert response.status_code == 200
    assert "text/csv" in response.headers["content-type"]
    assert "attachment" in response.headers["content-disposition"]

    csv_content = response.text
    assert "frame_number" in csv_content
    assert "psnr_y" in csv_content
    assert "vmaf" in csv_content
```

---

### 2.7 GET /health - 健康检查

**描述**: 返回服务健康状态（用于监控/负载均衡）

**请求**:

```
GET /health HTTP/1.1
Host: localhost:8080
```

**响应**:

```json
{
  "status": "healthy",
  "version": "0.1.0",
  "uptime_seconds": 3600.5,
  "checks": {
    "ffmpeg": "available",
    "vmaf_model": "available",
    "disk_space_gb": 150.3
  }
}
```

**状态码**:
- `200 OK`: 服务健康
- `503 Service Unavailable`: 服务不可用（FFmpeg 缺失、磁盘空间不足）

**契约测试**:

```python
def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data
    assert data["checks"]["ffmpeg"] == "available"
```

---

## 三、错误响应格式

### 3.1 验证错误（422）

```json
{
  "detail": [
    {
      "loc": ["body", "rate_control"],
      "msg": "值必须为 'abr' 或 'crf'",
      "type": "value_error.const"
    }
  ]
}
```

### 3.2 未找到资源（404）

```json
{
  "detail": "任务 ID 不存在: abc123def456"
}
```

### 3.3 冲突（409）

```json
{
  "detail": "任务尚未完成，当前状态: processing"
}
```

### 3.4 服务器错误（500）

```json
{
  "detail": "内部服务器错误",
  "error_id": "err_xyz789",
  "message": "FFmpeg 调用失败: timeout"
}
```

---

## 四、OpenAPI 规范（部分）

**完整规范见**: `/specs/001-video-quality-metrics-report/contracts/openapi.yaml`

```yaml
openapi: 3.0.3
info:
  title: VQMR API
  description: 视频质量指标报告系统 API
  version: 0.1.0

servers:
  - url: http://localhost:8080
    description: 开发服务器

paths:
  /jobs:
    post:
      summary: 创建编码任务
      operationId: create_job
      requestBody:
        required: true
        content:
          multipart/form-data:
            schema:
              $ref: '#/components/schemas/CreateJobRequest'
      responses:
        '303':
          description: 任务创建成功，重定向
          headers:
            Location:
              schema:
                type: string
                example: /jobs/abc123def456
        '422':
          description: 验证失败
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ValidationError'

components:
  schemas:
    CreateJobRequest:
      type: object
      required:
        - encoder_path
        - video_file
        - rate_control
        - rate_values
      properties:
        encoder_path:
          type: string
          example: /usr/bin/x264
        video_file:
          type: string
          format: binary
        rate_control:
          type: string
          enum: [abr, crf]
        rate_values:
          type: string
          example: "500,1000,2000"
```

---

## 五、安全考虑

### 5.1 路径遍历防护

```python
@app.get("/jobs/{job_id}")
async def get_job_report(job_id: str):
    # 验证 job_id 格式（仅允许字母数字）
    if not re.match(r'^[a-zA-Z0-9]{12}$', job_id):
        raise HTTPException(status_code=400, detail="无效的任务 ID 格式")

    job_dir = JOBS_ROOT / job_id[:2] / job_id
    if not job_dir.exists():
        raise HTTPException(status_code=404, detail="任务 ID 不存在")
```

### 5.2 文件上传限制

```python
@app.post("/jobs")
async def create_job(
    video_file: UploadFile = File(..., max_length=10 * 1024 * 1024 * 1024)  # 10GB
):
    # 验证 MIME 类型
    if not video_file.content_type.startswith("video/"):
        raise HTTPException(status_code=415, detail="不支持的媒体类型")
```

### 5.3 速率限制（可选）

```python
from fastapi_limiter import FastAPILimiter
from fastapi_limiter.depends import RateLimiter

@app.post("/jobs", dependencies=[Depends(RateLimiter(times=10, minutes=1))])
async def create_job(...):
    ...
```

---

## 六、契约测试清单

| 测试场景 | 端点 | 预期结果 |
|---------|------|---------|
| 上传页加载 | `GET /` | 200 OK, HTML |
| 创建任务成功 | `POST /jobs` | 303 See Other, Location 头 |
| 无效编码器路径 | `POST /jobs` | 422 Unprocessable Entity |
| 无效视频文件路径 | `POST /jobs` | 422 Unprocessable Entity |
| 无效码控模式 | `POST /jobs` | 422 Unprocessable Entity |
| 同时选择 ABR 和 CRF | `POST /jobs` | 422 Unprocessable Entity |
| 查看处理中任务 | `GET /jobs/{id}` | 200 OK, 进度条可见 |
| 查看已完成任务 | `GET /jobs/{id}` | 200 OK, Chart.js 图表 |
| 查看失败任务 | `GET /jobs/{id}` | 200 OK, 错误消息 |
| 任务不存在 | `GET /jobs/{id}` | 404 Not Found |
| 轮询任务状态 | `GET /jobs/{id}/status` | 200 OK, JSON 状态 |
| 下载 JSON 指标 | `GET /jobs/{id}/psnr.json` | 200 OK, 有效 JSON |
| 下载 CSV 指标 | `GET /jobs/{id}/psnr.csv` | 200 OK, CSV 格式 |
| 未完成任务下载 JSON | `GET /jobs/{id}/psnr.json` | 409 Conflict |
| 健康检查 | `GET /health` | 200 OK, status=healthy |

---

## 七、下一步

- [ ] 生成完整 OpenAPI YAML（`contracts/openapi.yaml`）
- [ ] 实现 FastAPI 路由（`backend/src/api/`）
- [ ] 编写契约测试（`backend/tests/contract/`）
- [ ] 验证与数据模型一致性

---

**设计完成日期**: 2025-10-25
**审查状态**: 待实现验证
