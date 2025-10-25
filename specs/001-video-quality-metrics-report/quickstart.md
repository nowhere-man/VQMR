# 快速启动指南：视频质量指标报告系统

**特性分支**: `001-video-quality-metrics-report`
**版本**: 0.1.0
**最后更新**: 2025-10-25

## 概述

本指南提供 VQMR 项目的快速启动步骤，包括环境准备、安装依赖、运行服务、提交任务和查看报告。

## 一、前置条件

### 1.1 系统要求

- **操作系统**: Linux / macOS / Windows
- **Python**: 3.10+
- **FFmpeg**: 5.0+（需包含 libvmaf 支持）
- **磁盘空间**: 至少 10GB 可用空间
- **内存**: 建议 4GB+ RAM

### 1.2 检查依赖

```bash
# 检查 Python 版本
python3 --version  # 应显示 Python 3.10.x 或更高

# 检查 FFmpeg
ffmpeg -version  # 应显示 FFmpeg 5.0.x 或更高

# 检查 VMAF 支持
ffmpeg -filters | grep vmaf  # 应显示 libvmaf 滤镜
```

---

## 二、安装

### 2.1 克隆仓库

```bash
git clone https://github.com/your-org/VQMR.git
cd VQMR
git checkout 001-video-quality-metrics-report
```

### 2.2 安装 Python 依赖

**方式 1: 使用 pip**

```bash
# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt
```

**方式 2: 使用 uv（推荐）**

```bash
# 安装 uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# 安装依赖
uv pip install -r requirements.txt
```

### 2.3 安装 FFmpeg（如果未安装）

**Linux (Ubuntu/Debian)**:

```bash
sudo apt update
sudo apt install -y ffmpeg
```

**macOS (Homebrew)**:

```bash
brew install ffmpeg
```

**Windows (Scoop)**:

```bash
scoop install ffmpeg
```

### 2.4 配置环境变量

```bash
# 复制配置模板
cp .env.example .env

# 编辑配置文件
nano .env
```

`.env` 文件示例：

```bash
# 服务器配置
HOST=0.0.0.0
PORT=8080

# 任务目录
JOBS_ROOT_DIR=./jobs

# FFmpeg 配置
FFMPEG_TIMEOUT=600
VMAF_MODEL_PATH=/usr/share/model/vmaf_v0.6.1.json

# 清理配置
RETENTION_DAYS=7
```

---

## 三、运行服务

### 3.1 启动开发服务器

```bash
# 激活虚拟环境
source venv/bin/activate

# 启动服务
uvicorn backend.src.main:app --host 0.0.0.0 --port 8080 --reload
```

**输出示例**:

```
INFO:     Uvicorn running on http://0.0.0.0:8080 (Press CTRL+C to quit)
INFO:     Started reloader process [12345] using WatchFiles
INFO:     Started server process [12346]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

### 3.2 验证服务

**方式 1: 浏览器访问**

打开浏览器访问: `http://localhost:8080`

应看到上传页面

**方式 2: curl 健康检查**

```bash
curl http://localhost:8080/health
```

预期输出：

```json
{
  "status": "healthy",
  "version": "0.1.0",
  "checks": {
    "ffmpeg": "available",
    "vmaf_model": "available"
  }
}
```

---

## 四、快速体验

### 4.1 准备测试视频

**方式 1: 使用示例视频**

```bash
# 下载示例视频（10 秒 1080p）
wget https://example.com/test_1080p_10s.mp4 -O test_video.mp4
```

**方式 2: 生成测试视频**

```bash
# 使用 FFmpeg 生成 10 秒彩色测试视频
ffmpeg -f lavfi -i testsrc=duration=10:size=1920x1080:rate=30 \
       -c:v libx264 -preset fast -crf 23 test_video.mp4
```

### 4.2 Web 界面提交任务

1. 访问 `http://localhost:8080`
2. 填写表单：
   - **编码器路径**: `/usr/bin/x264`（或 `ffmpeg` 的完整路径）
   - **上传视频**: 选择 `test_video.mp4`
   - **码控模式**: 选择 `ABR (平均码率)`
   - **码率值**: 输入 `1000` (kbps)
3. 点击"提交任务"
4. 自动跳转到任务详情页（`/jobs/{job_id}`）
5. 等待编码完成（进度条显示）
6. 查看可视化报告（Chart.js 图表）

### 4.3 命令行提交任务

```bash
curl -X POST http://localhost:8080/jobs \
  -F "encoder_path=/usr/bin/x264" \
  -F "video_file=@test_video.mp4" \
  -F "rate_control=abr" \
  -F "rate_values=1000"
```

**响应示例**:

```json
{
  "job_id": "abc123def456",
  "status": "queued",
  "created_at": "2025-10-25T10:30:00Z",
  "message": "任务已创建，正在处理中"
}
```

### 4.4 查询任务状态

```bash
curl http://localhost:8080/jobs/abc123def456/status
```

**响应示例（处理中）**:

```json
{
  "job_id": "abc123def456",
  "status": "processing",
  "progress": {
    "completed_tasks": 0,
    "total_tasks": 1,
    "progress_percent": 0.0
  }
}
```

### 4.5 下载指标数据

**JSON 格式**:

```bash
curl http://localhost:8080/jobs/abc123def456/psnr.json > metrics.json
```

**CSV 格式**:

```bash
curl http://localhost:8080/jobs/abc123def456/psnr.csv > metrics.csv
```

---

## 五、高级用法

### 5.1 多码率对比

```bash
# 提交多个码率值
curl -X POST http://localhost:8080/jobs \
  -F "encoder_path=/usr/bin/x264" \
  -F "video_file=@test_video.mp4" \
  -F "rate_control=abr" \
  -F "rate_values=500,1000,2000"  # 逗号分隔
```

### 5.2 CRF 模式

```bash
# 使用 CRF（恒定质量因子）
curl -X POST http://localhost:8080/jobs \
  -F "encoder_path=/usr/bin/x264" \
  -F "video_file=@test_video.mp4" \
  -F "rate_control=crf" \
  -F "rate_values=18,23,28"  # CRF 值：18(高质量), 23(默认), 28(低质量)
```

### 5.3 YUV 原始文件

```bash
# 提交 YUV 文件（需提供元数据）
curl -X POST http://localhost:8080/jobs \
  -F "encoder_path=/usr/bin/x264" \
  -F "video_file=@test.yuv" \
  -F "video_format=raw_yuv" \
  -F "yuv_resolution=1920x1080" \
  -F "yuv_pixel_format=yuv420p" \
  -F "yuv_frame_rate=30.0" \
  -F "rate_control=abr" \
  -F "rate_values=2000"
```

---

## 六、Docker 部署（可选）

### 6.1 构建镜像

```bash
docker build -t vqmr:0.1.0 .
```

### 6.2 运行容器

```bash
docker run -d \
  --name vqmr-server \
  -p 8080:8080 \
  -v $(pwd)/jobs:/app/jobs \
  -e JOBS_ROOT_DIR=/app/jobs \
  vqmr:0.1.0
```

### 6.3 使用 Docker Compose

```bash
# 启动服务
docker-compose up -d

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down
```

`docker-compose.yml` 示例：

```yaml
version: '3.8'

services:
  vqmr:
    build: .
    ports:
      - "8080:8080"
    volumes:
      - ./jobs:/app/jobs
    environment:
      - HOST=0.0.0.0
      - PORT=8080
      - JOBS_ROOT_DIR=/app/jobs
    restart: unless-stopped
```

---

## 七、故障排查

### 7.1 常见问题

**问题 1: FFmpeg 未找到**

```
错误: 编码器文件不存在: /usr/bin/x264
```

**解决方案**:

```bash
# 查找 FFmpeg 安装路径
which ffmpeg

# 或使用完整路径
/usr/local/bin/ffmpeg
```

**问题 2: VMAF 模型缺失**

```
错误: VMAF model file not found
```

**解决方案**:

```bash
# Linux
sudo apt install libvmaf-dev

# macOS
brew install libvmaf

# 或手动下载模型
wget https://github.com/Netflix/vmaf/raw/master/model/vmaf_v0.6.1.json \
     -O /usr/share/model/vmaf_v0.6.1.json
```

**问题 3: 端口被占用**

```
错误: [Errno 48] Address already in use
```

**解决方案**:

```bash
# 更换端口
uvicorn backend.src.main:app --port 8081

# 或终止占用进程
lsof -ti:8080 | xargs kill
```

### 7.2 日志查看

```bash
# 查看应用日志
tail -f logs/vqmr.log

# 查看任务日志
cat jobs/ab/abc123def456/encoding.log
```

---

## 八、下一步

### 8.1 开发指南

- **数据模型**: 查看 `specs/001-video-quality-metrics-report/data-model.md`
- **API 契约**: 查看 `specs/001-video-quality-metrics-report/contracts/README.md`
- **测试**: 运行 `pytest backend/tests/`

### 8.2 生产部署

- **Nginx 反向代理**: 参见 `docs/deployment.md`
- **Systemd 服务**: 参见 `scripts/systemd/vqmr.service`
- **定时清理**: 配置 cron 任务（`scripts/cleanup_jobs.py`）

### 8.3 性能优化

- **并发限制**: 调整 `UVICORN_WORKERS` 环境变量
- **任务队列**: 考虑集成 Celery（高负载场景）
- **缓存**: 启用 HTTP 缓存（Nginx/CDN）

---

## 九、API 速查

| 端点 | 方法 | 描述 |
|------|------|------|
| `/` | GET | 上传页面 |
| `/jobs` | POST | 创建任务 |
| `/jobs/{id}` | GET | 报告页面 |
| `/jobs/{id}/status` | GET | 任务状态（JSON） |
| `/jobs/{id}/psnr.json` | GET | 质量指标（JSON） |
| `/jobs/{id}/psnr.csv` | GET | 质量指标（CSV） |
| `/health` | GET | 健康检查 |

---

## 十、支持资源

### 10.1 文档

- **功能规格**: `specs/001-video-quality-metrics-report/spec.md`
- **实施计划**: `specs/001-video-quality-metrics-report/plan.md`
- **技术研究**: `specs/001-video-quality-metrics-report/research.md`

### 10.2 示例

- **Chart.js 示例**: `specs/001-video-quality-metrics-report/examples/`
- **Pytest 测试**: `backend/tests/`

### 10.3 外部资源

- [FastAPI 官方文档](https://fastapi.tiangolo.com/)
- [FFmpeg 官方文档](https://ffmpeg.org/documentation.html)
- [Chart.js 官方文档](https://www.chartjs.org/)
- [VMAF 项目](https://github.com/Netflix/vmaf)

---

## 十一、反馈与贡献

### 11.1 问题报告

如遇到问题，请提交 Issue 并附上：
- 操作系统与 Python 版本
- FFmpeg 版本
- 完整错误日志
- 重现步骤

### 11.2 功能建议

欢迎提交 Pull Request 或 Feature Request。

---

**版本**: 0.1.0 | **最后更新**: 2025-10-25 | **许可证**: MIT
