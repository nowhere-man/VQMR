# 研究报告：基于文件系统的任务管理模式（无数据库方案）

**项目**: VQMR (Video Quality Metrics Report)
**分支**: `001-video-quality-metrics-report`
**日期**: 2025-10-25
**作者**: Research Phase

---

## 目录

1. [目录结构设计](#1-目录结构设计)
2. [任务 ID 生成策略](#2-任务-id-生成策略)
3. [状态管理与原子性](#3-状态管理与原子性)
4. [数据持久化策略](#4-数据持久化策略)
5. [清理策略](#5-清理策略)
6. [错误恢复机制](#6-错误恢复机制)
7. [Python 实现示例](#7-python-实现示例)
8. [最佳实践与陷阱](#8-最佳实践与陷阱)

---

## 1. 目录结构设计

### 1.1 推荐目录结构

```text
jobs/
├── metadata.db.json           # 全局索引（可选，用于快速查询）
├── .cleanup.lock              # 清理进程锁文件
├── ab/                        # 两级分桶（job_id 前两个字符）
│   └── cd1234567890/          # 完整 job_id
│       ├── .lock              # 任务锁文件（PID 锁）
│       ├── metadata.json      # 任务元数据与状态
│       ├── metadata.json.tmp  # 临时文件（原子写入）
│       ├── input.mp4          # 原始视频
│       ├── output.mp4         # 编码输出
│       ├── psnr.log           # FFmpeg 原始日志
│       ├── psnr.json          # 解析后的 JSON 结果
│       ├── psnr.csv           # 可下载的 CSV
│       ├── vmaf.json          # VMAF 指标
│       ├── ssim.json          # SSIM 指标
│       └── performance.json   # 性能指标（CPU、延迟）
├── ef/
│   └── gh5678901234/
│       └── ...
└── archive/                   # 归档目录（7 天后移动至此）
    └── 2025-10-18/            # 按日期归档
        └── ab/
            └── cd1234567890/
                └── ...
```

### 1.2 分桶策略选择

| 方案 | 优点 | 缺点 | 适用场景 |
|------|------|------|----------|
| **单层目录** (`jobs/{job_id}/`) | 简单，易于实现 | 文件系统性能下降（>10,000 任务） | 小型部署（<5000 任务/月） |
| **两级分桶** (`jobs/{prefix}/{job_id}/`) | 平衡性能与复杂度 | 需要额外路径解析 | **推荐方案**（中型部署） |
| **三级分桶** (`jobs/{p1}/{p2}/{job_id}/`) | 极高性能 | 过度复杂 | 超大规模部署（>1M 任务/月） |

**推荐**: 采用**两级分桶**（取 job_id 前两个字符作为前缀），可支持约 256 个子目录（16^2），每个子目录平均分布 ~390 个任务（假设 10 万任务）。

### 1.3 文件命名规范

```python
# 固定文件名（避免硬编码）
METADATA_FILE = "metadata.json"
METADATA_TMP = "metadata.json.tmp"
LOCK_FILE = ".lock"
INPUT_VIDEO = "input.mp4"      # 或根据实际格式命名
OUTPUT_VIDEO = "output.mp4"
PSNR_LOG = "psnr.log"
PSNR_JSON = "psnr.json"
PSNR_CSV = "psnr.csv"
VMAF_JSON = "vmaf.json"
SSIM_JSON = "ssim.json"
PERF_JSON = "performance.json"
```

---

## 2. 任务 ID 生成策略

### 2.1 方案对比

| 方案 | 示例 | 长度 | 优点 | 缺点 | 适用场景 |
|------|------|------|------|------|----------|
| **UUID v4** | `550e8400-e29b-41d4-a716-446655440000` | 36 字符 | 完全随机，无碰撞 | 冗长，URL 不友好 | 需要强随机性 |
| **nanoid** | `V1StGXR8_Z5jdHi6B-myT` | 21 字符（可配置） | URL 安全，短小 | 需要额外依赖 | **推荐方案** |
| **时间戳 + 随机** | `20251025143022-a3f9` | 19 字符 | 可排序，易调试 | 时间同步依赖 | 需要时间排序 |
| **短 UUID** | `abcd1234ef567890` | 16 字符 | 紧凑，固定长度 | 碰撞概率稍高 | 内部系统 |

### 2.2 推荐方案：nanoid（自定义字母表）

```python
from nanoid import generate

# 自定义字母表（去除易混淆字符：0/O, 1/I/l）
ALPHABET = "23456789abcdefghjkmnpqrstuvwxyzABCDEFGHJKMNPQRSTUVWXYZ"

def generate_job_id(length: int = 12) -> str:
    """
    生成任务 ID（nanoid）

    Args:
        length: ID 长度（默认 12，碰撞概率 < 1% 需要 ~100 亿次生成）

    Returns:
        任务 ID（例如：3f8d9n2k4pqr）
    """
    return generate(alphabet=ALPHABET, size=length)

# 碰撞概率计算（生日悖论）
# P(collision) ≈ n^2 / (2 * 54^12)
# 对于 1M 任务：P ≈ 0.0000003%（可忽略）
```

### 2.3 避免枚举攻击

```python
# ❌ 不安全：使用递增 ID
job_id = "job-000001"  # 攻击者可遍历所有任务

# ✅ 安全：随机 ID + 权限校验
job_id = generate_job_id()  # 3f8d9n2k4pqr
# 额外措施：添加访问 token（可选）
access_token = secrets.token_urlsafe(16)  # 存储在 metadata.json
```

---

## 3. 状态管理与原子性

### 3.1 状态机定义

```python
from enum import Enum

class TaskStatus(str, Enum):
    QUEUED = "queued"           # 已入队，等待处理
    PROCESSING = "processing"   # 正在编码/计算指标
    COMPLETED = "completed"     # 成功完成
    FAILED = "failed"           # 失败（含错误信息）
    CANCELLED = "cancelled"     # 用户取消（可选）

# 状态转换规则
VALID_TRANSITIONS = {
    TaskStatus.QUEUED: [TaskStatus.PROCESSING, TaskStatus.CANCELLED],
    TaskStatus.PROCESSING: [TaskStatus.COMPLETED, TaskStatus.FAILED],
    TaskStatus.COMPLETED: [],  # 终态
    TaskStatus.FAILED: [],      # 终态
    TaskStatus.CANCELLED: [],   # 终态
}
```

### 3.2 metadata.json 格式定义

```json
{
  "job_id": "3f8d9n2k4pqr",
  "status": "completed",
  "created_at": "2025-10-25T14:30:22.123456Z",
  "updated_at": "2025-10-25T14:35:18.987654Z",
  "started_at": "2025-10-25T14:30:25.234567Z",
  "completed_at": "2025-10-25T14:35:18.987654Z",
  "encoder": {
    "path": "/usr/bin/ffmpeg",
    "version": "5.1.2"
  },
  "input_video": {
    "path": "/data/videos/source.mp4",
    "format": "mp4",
    "duration": 10.5,
    "resolution": "1920x1080",
    "fps": 30,
    "codec": "h264"
  },
  "encoding_params": {
    "mode": "abr",
    "bitrate": 2000,
    "preset": "medium"
  },
  "output_video": {
    "path": "output.mp4",
    "size_bytes": 2621440,
    "actual_bitrate": 1998.3
  },
  "metrics": {
    "psnr": {
      "avg": 42.35,
      "min": 38.12,
      "max": 45.67
    },
    "vmaf": {
      "avg": 95.2,
      "min": 92.1,
      "max": 98.5
    },
    "ssim": {
      "avg": 0.982,
      "min": 0.975,
      "max": 0.991
    }
  },
  "performance": {
    "encoding_time_sec": 293.5,
    "encoding_speed_fps": 30.2,
    "cpu_usage_percent": 87.3,
    "frame_latency_ms": {
      "avg": 33.1,
      "min": 28.5,
      "max": 42.7
    }
  },
  "error": null,
  "access_token": "AbCdEfGhIjKlMnOpQrStUvWxYz123456"
}
```

### 3.3 原子性写入（临时文件 + rename）

```python
import json
import os
from pathlib import Path
from typing import Any, Dict

def atomic_write_json(file_path: Path, data: Dict[str, Any]) -> None:
    """
    原子性写入 JSON 文件（通过 rename 保证）

    Args:
        file_path: 目标文件路径
        data: 要写入的数据

    Raises:
        IOError: 写入失败
    """
    tmp_path = file_path.with_suffix(".json.tmp")

    try:
        # 1. 写入临时文件
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.flush()
            os.fsync(f.fileno())  # 强制刷新到磁盘

        # 2. 原子性重命名（POSIX 保证原子性）
        tmp_path.rename(file_path)

    except Exception as e:
        # 清理临时文件
        if tmp_path.exists():
            tmp_path.unlink()
        raise IOError(f"原子写入失败: {e}")

def read_metadata(job_dir: Path) -> Dict[str, Any]:
    """读取任务元数据"""
    metadata_file = job_dir / "metadata.json"
    if not metadata_file.exists():
        raise FileNotFoundError(f"元数据文件不存在: {metadata_file}")

    with open(metadata_file, "r", encoding="utf-8") as f:
        return json.load(f)

def update_metadata(job_dir: Path, updates: Dict[str, Any]) -> None:
    """更新任务元数据（部分更新）"""
    metadata = read_metadata(job_dir)
    metadata.update(updates)
    metadata["updated_at"] = datetime.utcnow().isoformat() + "Z"
    atomic_write_json(job_dir / "metadata.json", metadata)
```

### 3.4 并发访问控制（文件锁）

```python
import fcntl
import os
import time
from contextlib import contextmanager
from pathlib import Path

@contextmanager
def file_lock(lock_path: Path, timeout: int = 10):
    """
    文件锁上下文管理器（阻塞式）

    Args:
        lock_path: 锁文件路径
        timeout: 超时时间（秒）

    Yields:
        锁文件句柄

    Raises:
        TimeoutError: 获取锁超时
    """
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    lock_file = None
    start_time = time.time()

    try:
        lock_file = open(lock_path, "w")

        # 尝试获取排他锁（阻塞式）
        while True:
            try:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if time.time() - start_time > timeout:
                    raise TimeoutError(f"获取锁超时: {lock_path}")
                time.sleep(0.1)

        # 写入当前进程 PID
        lock_file.write(str(os.getpid()))
        lock_file.flush()

        yield lock_file

    finally:
        if lock_file:
            try:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
                lock_file.close()
                lock_path.unlink()  # 删除锁文件
            except Exception:
                pass

# 使用示例
def update_task_status(job_id: str, status: TaskStatus):
    job_dir = get_job_dir(job_id)
    lock_path = job_dir / ".lock"

    with file_lock(lock_path):
        metadata = read_metadata(job_dir)

        # 验证状态转换合法性
        current_status = TaskStatus(metadata["status"])
        if status not in VALID_TRANSITIONS.get(current_status, []):
            raise ValueError(f"非法状态转换: {current_status} -> {status}")

        update_metadata(job_dir, {
            "status": status.value,
            "updated_at": datetime.utcnow().isoformat() + "Z"
        })
```

---

## 4. 数据持久化策略

### 4.1 JSON 文件解析与更新

```python
from typing import Optional
from pydantic import BaseModel, Field
from datetime import datetime

class EncoderInfo(BaseModel):
    path: str
    version: Optional[str] = None

class VideoInfo(BaseModel):
    path: str
    format: str
    duration: Optional[float] = None
    resolution: Optional[str] = None
    fps: Optional[int] = None
    codec: Optional[str] = None

class MetricsData(BaseModel):
    psnr: Optional[Dict[str, float]] = None
    vmaf: Optional[Dict[str, float]] = None
    ssim: Optional[Dict[str, float]] = None

class TaskMetadata(BaseModel):
    job_id: str
    status: TaskStatus
    created_at: datetime
    updated_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    encoder: EncoderInfo
    input_video: VideoInfo
    encoding_params: Dict[str, Any]
    output_video: Optional[Dict[str, Any]] = None
    metrics: Optional[MetricsData] = None
    performance: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    access_token: str = Field(default_factory=lambda: secrets.token_urlsafe(16))

    class Config:
        use_enum_values = True

# 类型安全的读写
def save_metadata(job_dir: Path, metadata: TaskMetadata):
    atomic_write_json(
        job_dir / "metadata.json",
        metadata.model_dump(mode="json")
    )

def load_metadata(job_dir: Path) -> TaskMetadata:
    data = read_metadata(job_dir)
    return TaskMetadata.model_validate(data)
```

### 4.2 CSV 导出生成策略

```python
import csv
from pathlib import Path
from typing import List, Dict

def generate_psnr_csv(job_dir: Path, frame_data: List[Dict[str, Any]]) -> Path:
    """
    生成 PSNR 逐帧 CSV 文件

    Args:
        job_dir: 任务目录
        frame_data: 逐帧数据（从 psnr.json 读取）

    Returns:
        CSV 文件路径
    """
    csv_path = job_dir / "psnr.csv"

    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "frame_number",
            "timestamp_sec",
            "psnr_y",
            "psnr_u",
            "psnr_v",
            "psnr_avg"
        ])
        writer.writeheader()
        writer.writerows(frame_data)

    return csv_path

# 批量导出所有指标
def export_all_metrics(job_dir: Path):
    """导出所有指标为 CSV"""
    metrics = ["psnr", "vmaf", "ssim"]

    for metric in metrics:
        json_file = job_dir / f"{metric}.json"
        if not json_file.exists():
            continue

        with open(json_file, "r") as f:
            data = json.load(f)

        csv_file = job_dir / f"{metric}.csv"
        with open(csv_file, "w", newline="", encoding="utf-8") as f:
            if data:
                writer = csv.DictWriter(f, fieldnames=data[0].keys())
                writer.writeheader()
                writer.writerows(data)
```

### 4.3 日志文件滚动与归档

```python
import logging
from logging.handlers import RotatingFileHandler

def setup_task_logger(job_dir: Path, job_id: str) -> logging.Logger:
    """
    为单个任务设置日志记录器

    Args:
        job_dir: 任务目录
        job_id: 任务 ID

    Returns:
        配置好的日志记录器
    """
    logger = logging.getLogger(f"task.{job_id}")
    logger.setLevel(logging.DEBUG)

    # 文件处理器（滚动日志，最大 10MB，保留 3 个备份）
    log_file = job_dir / "task.log"
    handler = RotatingFileHandler(
        log_file,
        maxBytes=10 * 1024 * 1024,  # 10 MB
        backupCount=3,
        encoding="utf-8"
    )

    # JSON 格式日志（结构化）
    formatter = logging.Formatter(
        '{"timestamp": "%(asctime)s", "level": "%(levelname)s", '
        '"job_id": "' + job_id + '", "module": "%(name)s", '
        '"message": "%(message)s"}'
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    return logger
```

---

## 5. 清理策略

### 5.1 自动清理策略选择

| 方案 | 触发时机 | 优点 | 缺点 | 适用场景 |
|------|---------|------|------|----------|
| **Cron 定时任务** | 每天凌晨 2:00 | 独立进程，不影响应用 | 需要系统配置 | **推荐方案**（生产环境） |
| **应用启动时** | FastAPI `@app.on_event("startup")` | 无需外部依赖 | 延迟启动时间 | 开发/测试环境 |
| **后台线程** | 应用启动后周期运行 | 实时清理 | 占用应用资源 | 轻量级部署 |
| **手动触发** | API 端点 `/admin/cleanup` | 完全控制 | 易忘记 | 小型部署 |

### 5.2 Cron 定时任务实现

```bash
# /etc/cron.d/vqmr-cleanup
# 每天凌晨 2:00 执行清理任务
0 2 * * * /usr/bin/python3 /path/to/vqmr/cleanup.py >> /var/log/vqmr-cleanup.log 2>&1
```

```python
#!/usr/bin/env python3
"""
cleanup.py - 任务清理脚本

用法:
    python cleanup.py --days 7 --dry-run
"""
import argparse
import shutil
from datetime import datetime, timedelta
from pathlib import Path

JOBS_DIR = Path("/path/to/jobs")
ARCHIVE_DIR = Path("/path/to/archive")
CLEANUP_LOCK = JOBS_DIR / ".cleanup.lock"

def cleanup_old_tasks(days: int, dry_run: bool = False):
    """
    清理指定天数前的任务

    Args:
        days: 保留天数（默认 7 天）
        dry_run: 仅打印，不实际删除
    """
    cutoff_date = datetime.utcnow() - timedelta(days=days)

    # 获取全局锁（避免并发清理）
    try:
        with file_lock(CLEANUP_LOCK, timeout=5):
            tasks_cleaned = 0
            total_size = 0

            # 遍历所有任务目录（两级分桶）
            for prefix_dir in JOBS_DIR.iterdir():
                if not prefix_dir.is_dir() or prefix_dir.name.startswith("."):
                    continue

                for job_dir in prefix_dir.iterdir():
                    if not job_dir.is_dir():
                        continue

                    # 检查任务是否已完成且超过保留期
                    try:
                        metadata = read_metadata(job_dir)
                        completed_at = datetime.fromisoformat(
                            metadata["completed_at"].replace("Z", "+00:00")
                        )

                        if completed_at < cutoff_date:
                            # 计算目录大小
                            size = sum(f.stat().st_size for f in job_dir.rglob("*") if f.is_file())
                            total_size += size

                            if dry_run:
                                print(f"[DRY-RUN] 将删除: {job_dir} ({size / 1024 / 1024:.2f} MB)")
                            else:
                                # 归档（可选）
                                archive_date = completed_at.strftime("%Y-%m-%d")
                                archive_path = ARCHIVE_DIR / archive_date / prefix_dir.name / job_dir.name
                                archive_path.parent.mkdir(parents=True, exist_ok=True)
                                shutil.move(str(job_dir), str(archive_path))
                                print(f"已归档: {job_dir} -> {archive_path}")

                            tasks_cleaned += 1

                    except Exception as e:
                        print(f"跳过任务 {job_dir}: {e}")

            print(f"清理完成: {tasks_cleaned} 个任务, 释放 {total_size / 1024 / 1024:.2f} MB")

    except TimeoutError:
        print("清理进程已在运行，跳过本次清理")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="VQMR 任务清理工具")
    parser.add_argument("--days", type=int, default=7, help="保留天数（默认 7）")
    parser.add_argument("--dry-run", action="store_true", help="仅打印，不实际删除")
    args = parser.parse_args()

    cleanup_old_tasks(args.days, args.dry_run)
```

### 5.3 防止清理时的并发写入

```python
def safe_delete_job(job_id: str) -> bool:
    """
    安全删除任务（获取锁后删除）

    Returns:
        True 表示删除成功，False 表示任务正在使用
    """
    job_dir = get_job_dir(job_id)
    lock_path = job_dir / ".lock"

    try:
        # 尝试非阻塞获取锁
        with open(lock_path, "w") as lock_file:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)

            # 获取锁成功，删除目录
            shutil.rmtree(job_dir)
            return True

    except BlockingIOError:
        # 任务正在使用，跳过删除
        return False
    except FileNotFoundError:
        # 锁文件不存在，直接删除
        shutil.rmtree(job_dir, ignore_errors=True)
        return True
```

---

## 6. 错误恢复机制

### 6.1 任务中断后的状态恢复

```python
def recover_interrupted_tasks():
    """
    应用启动时恢复中断的任务

    策略:
    1. 扫描所有 status=processing 的任务
    2. 检查 .lock 文件中的 PID 是否仍在运行
    3. 如 PID 不存在，标记任务为 failed
    """
    for job_dir in iter_all_jobs():
        try:
            metadata = read_metadata(job_dir)

            if metadata["status"] == TaskStatus.PROCESSING.value:
                lock_path = job_dir / ".lock"

                if not is_process_alive(lock_path):
                    # 进程已死亡，标记为失败
                    update_metadata(job_dir, {
                        "status": TaskStatus.FAILED.value,
                        "error": "任务中断（进程异常退出）",
                        "completed_at": datetime.utcnow().isoformat() + "Z"
                    })
                    print(f"恢复任务 {metadata['job_id']}: 标记为失败")

        except Exception as e:
            print(f"恢复任务失败 {job_dir}: {e}")

def is_process_alive(lock_path: Path) -> bool:
    """检查锁文件中的 PID 是否仍在运行"""
    if not lock_path.exists():
        return False

    try:
        with open(lock_path, "r") as f:
            pid = int(f.read().strip())

        # 检查进程是否存在（跨平台）
        os.kill(pid, 0)  # 信号 0 不会杀死进程，仅检查存在性
        return True

    except (ValueError, ProcessLookupError, PermissionError):
        return False

def iter_all_jobs():
    """迭代所有任务目录"""
    for prefix_dir in JOBS_DIR.iterdir():
        if not prefix_dir.is_dir() or prefix_dir.name.startswith("."):
            continue
        for job_dir in prefix_dir.iterdir():
            if job_dir.is_dir():
                yield job_dir
```

### 6.2 临时文件的孤儿清理

```python
def cleanup_orphan_temp_files():
    """
    清理孤儿临时文件（.tmp、.lock）

    策略:
    1. 查找所有 *.json.tmp 文件
    2. 检查修改时间 > 1 小时的临时文件
    3. 删除（说明写入已失败）
    """
    for job_dir in iter_all_jobs():
        # 清理临时 JSON 文件
        for tmp_file in job_dir.glob("*.tmp"):
            age = time.time() - tmp_file.stat().st_mtime
            if age > 3600:  # 1 小时
                tmp_file.unlink()
                print(f"删除孤儿文件: {tmp_file}")

        # 清理死锁文件
        lock_file = job_dir / ".lock"
        if lock_file.exists() and not is_process_alive(lock_file):
            lock_file.unlink()
            print(f"删除死锁文件: {lock_file}")
```

### 6.3 磁盘空间不足处理

```python
import shutil

def check_disk_space(min_free_gb: int = 10) -> bool:
    """
    检查磁盘剩余空间

    Args:
        min_free_gb: 最小空闲空间（GB）

    Returns:
        True 表示空间充足
    """
    stat = shutil.disk_usage(JOBS_DIR)
    free_gb = stat.free / (1024 ** 3)

    if free_gb < min_free_gb:
        print(f"警告: 磁盘空间不足（剩余 {free_gb:.2f} GB）")
        return False

    return True

def handle_disk_full_error(job_id: str, error: Exception):
    """
    磁盘空间不足时的处理

    策略:
    1. 标记任务为失败
    2. 删除未完成的输出文件
    3. 触发紧急清理（删除最旧的 10% 已完成任务）
    """
    job_dir = get_job_dir(job_id)

    # 标记失败
    update_metadata(job_dir, {
        "status": TaskStatus.FAILED.value,
        "error": f"磁盘空间不足: {error}"
    })

    # 删除部分输出
    for file in ["output.mp4", "psnr.log"]:
        (job_dir / file).unlink(missing_ok=True)

    # 触发紧急清理
    emergency_cleanup(percent=10)

def emergency_cleanup(percent: int = 10):
    """
    紧急清理：删除最旧的已完成任务

    Args:
        percent: 清理百分比（默认 10%）
    """
    completed_tasks = []

    for job_dir in iter_all_jobs():
        try:
            metadata = read_metadata(job_dir)
            if metadata["status"] == TaskStatus.COMPLETED.value:
                completed_tasks.append((
                    job_dir,
                    datetime.fromisoformat(metadata["completed_at"].replace("Z", "+00:00"))
                ))
        except Exception:
            pass

    # 按完成时间排序
    completed_tasks.sort(key=lambda x: x[1])

    # 删除最旧的 N%
    to_delete = int(len(completed_tasks) * percent / 100)
    for job_dir, _ in completed_tasks[:to_delete]:
        shutil.rmtree(job_dir, ignore_errors=True)
        print(f"紧急清理: {job_dir}")
```

---

## 7. Python 实现示例

### 7.1 完整任务管理类

```python
from pathlib import Path
from typing import Optional
import secrets
import json
import logging

class TaskManager:
    """基于文件系统的任务管理器"""

    def __init__(self, jobs_dir: Path):
        self.jobs_dir = jobs_dir
        self.jobs_dir.mkdir(parents=True, exist_ok=True)

    def get_job_dir(self, job_id: str) -> Path:
        """获取任务目录（两级分桶）"""
        prefix = job_id[:2]
        return self.jobs_dir / prefix / job_id

    def create_task(
        self,
        encoder_path: str,
        input_video_path: str,
        encoding_params: dict
    ) -> str:
        """
        创建新任务

        Returns:
            任务 ID
        """
        # 1. 生成任务 ID
        job_id = generate_job_id()
        job_dir = self.get_job_dir(job_id)
        job_dir.mkdir(parents=True, exist_ok=True)

        # 2. 创建元数据
        metadata = TaskMetadata(
            job_id=job_id,
            status=TaskStatus.QUEUED,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            encoder=EncoderInfo(path=encoder_path),
            input_video=VideoInfo(path=input_video_path, format="mp4"),
            encoding_params=encoding_params
        )

        # 3. 保存元数据
        save_metadata(job_dir, metadata)

        # 4. 设置日志记录器
        logger = setup_task_logger(job_dir, job_id)
        logger.info(f"任务已创建: {job_id}")

        return job_id

    def update_status(
        self,
        job_id: str,
        status: TaskStatus,
        error: Optional[str] = None
    ):
        """更新任务状态（带锁）"""
        job_dir = self.get_job_dir(job_id)
        lock_path = job_dir / ".lock"

        with file_lock(lock_path):
            metadata = load_metadata(job_dir)

            # 验证状态转换
            if status not in VALID_TRANSITIONS.get(metadata.status, []):
                raise ValueError(f"非法状态转换: {metadata.status} -> {status}")

            # 更新字段
            updates = {
                "status": status.value,
                "updated_at": datetime.utcnow().isoformat() + "Z"
            }

            if status == TaskStatus.PROCESSING and not metadata.started_at:
                updates["started_at"] = datetime.utcnow().isoformat() + "Z"

            if status in [TaskStatus.COMPLETED, TaskStatus.FAILED]:
                updates["completed_at"] = datetime.utcnow().isoformat() + "Z"

            if error:
                updates["error"] = error

            update_metadata(job_dir, updates)

    def get_task(self, job_id: str) -> Optional[TaskMetadata]:
        """获取任务元数据"""
        job_dir = self.get_job_dir(job_id)
        if not job_dir.exists():
            return None

        try:
            return load_metadata(job_dir)
        except Exception:
            return None

    def list_tasks(
        self,
        status: Optional[TaskStatus] = None,
        limit: int = 100
    ) -> List[TaskMetadata]:
        """列出任务（按创建时间倒序）"""
        tasks = []

        for job_dir in iter_all_jobs():
            try:
                metadata = load_metadata(job_dir)
                if status is None or metadata.status == status:
                    tasks.append(metadata)
            except Exception:
                pass

        # 按创建时间倒序排序
        tasks.sort(key=lambda x: x.created_at, reverse=True)
        return tasks[:limit]

    def delete_task(self, job_id: str) -> bool:
        """删除任务"""
        return safe_delete_job(job_id)
```

### 7.2 FastAPI 集成示例

```python
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel

app = FastAPI()
task_manager = TaskManager(Path("/data/jobs"))

class CreateTaskRequest(BaseModel):
    encoder_path: str
    input_video_path: str
    encoding_params: dict

class TaskResponse(BaseModel):
    job_id: str
    status: str
    created_at: str

@app.on_event("startup")
async def startup_event():
    """应用启动时恢复中断任务"""
    recover_interrupted_tasks()
    cleanup_orphan_temp_files()

@app.post("/tasks", response_model=TaskResponse)
async def create_task(request: CreateTaskRequest, background_tasks: BackgroundTasks):
    """创建编码任务"""
    # 检查磁盘空间
    if not check_disk_space():
        raise HTTPException(status_code=507, detail="磁盘空间不足")

    # 创建任务
    job_id = task_manager.create_task(
        request.encoder_path,
        request.input_video_path,
        request.encoding_params
    )

    # 后台执行编码
    background_tasks.add_task(process_encoding_task, job_id)

    metadata = task_manager.get_task(job_id)
    return TaskResponse(
        job_id=metadata.job_id,
        status=metadata.status.value,
        created_at=metadata.created_at.isoformat()
    )

@app.get("/tasks/{job_id}", response_model=TaskResponse)
async def get_task(job_id: str):
    """获取任务状态"""
    metadata = task_manager.get_task(job_id)
    if not metadata:
        raise HTTPException(status_code=404, detail="任务不存在")

    return TaskResponse(
        job_id=metadata.job_id,
        status=metadata.status.value,
        created_at=metadata.created_at.isoformat()
    )

def process_encoding_task(job_id: str):
    """后台任务：执行编码"""
    try:
        # 更新状态为处理中
        task_manager.update_status(job_id, TaskStatus.PROCESSING)

        # 执行编码（调用 FFmpeg）
        # ... 编码逻辑 ...

        # 更新状态为完成
        task_manager.update_status(job_id, TaskStatus.COMPLETED)

    except Exception as e:
        task_manager.update_status(job_id, TaskStatus.FAILED, str(e))
```

---

## 8. 最佳实践与陷阱

### 8.1 最佳实践

#### 1. 目录结构
- ✅ **使用两级分桶**（`jobs/{prefix}/{job_id}/`）平衡性能与复杂度
- ✅ **固定文件命名**（通过常量管理，避免硬编码）
- ✅ **预留扩展性**（metadata.json 支持额外字段）

#### 2. ID 生成
- ✅ **优先使用 nanoid**（短小、URL 安全、碰撞概率低）
- ✅ **自定义字母表**（去除易混淆字符：0/O, 1/I/l）
- ✅ **长度至少 12 字符**（碰撞概率 < 0.0001%）

#### 3. 原子性与并发
- ✅ **使用临时文件 + rename**（POSIX 保证原子性）
- ✅ **写入前 fsync**（强制刷新到磁盘）
- ✅ **使用文件锁**（`fcntl.flock`，跨进程可靠）
- ✅ **验证状态转换**（避免非法状态变更）

#### 4. 错误处理
- ✅ **应用启动时恢复中断任务**（检查 PID 存活性）
- ✅ **定期清理孤儿文件**（.tmp、.lock）
- ✅ **磁盘空间监控**（提前预警 + 紧急清理）

#### 5. 性能优化
- ✅ **延迟加载元数据**（列表页仅显示基础信息）
- ✅ **批量导出 CSV**（仅在用户请求时生成）
- ✅ **日志滚动**（避免单文件过大）

#### 6. 清理策略
- ✅ **Cron 定时任务**（独立进程，不影响应用）
- ✅ **归档而非删除**（7 天后移至 archive/）
- ✅ **清理前获取全局锁**（避免并发清理）

### 8.2 常见陷阱

#### 1. 文件系统限制

```python
# ❌ 错误：单目录存储过多文件（>10,000）
jobs/
└── job-000001/
└── job-000002/
└── ...
└── job-999999/  # 性能急剧下降！

# ✅ 正确：使用分桶
jobs/
├── ab/
│   └── abcd1234/
├── cd/
│   └── cdef5678/
```

#### 2. 非原子性写入

```python
# ❌ 错误：直接写入（可能产生半成品文件）
with open("metadata.json", "w") as f:
    json.dump(data, f)
    # 此时如果崩溃，文件可能损坏！

# ✅ 正确：临时文件 + rename
with open("metadata.json.tmp", "w") as f:
    json.dump(data, f)
    f.flush()
    os.fsync(f.fileno())
os.rename("metadata.json.tmp", "metadata.json")
```

#### 3. 竞态条件

```python
# ❌ 错误：先检查后操作（TOCTOU 漏洞）
if not lock_file.exists():
    # 此时其他进程可能已创建锁！
    create_lock()

# ✅ 正确：使用原子操作
try:
    fd = os.open(lock_file, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    os.close(fd)
except FileExistsError:
    # 锁已存在
    pass
```

#### 4. 锁未释放

```python
# ❌ 错误：手动管理锁（容易忘记释放）
lock_file = open(".lock", "w")
fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
# ... 操作 ...
# 如果抛异常，锁永远不释放！

# ✅ 正确：使用上下文管理器
with file_lock(lock_path):
    # ... 操作 ...
    pass  # 自动释放锁
```

#### 5. 状态不一致

```python
# ❌ 错误：多次更新元数据（非原子性）
metadata["status"] = "processing"
save_metadata(metadata)
# ... 编码 ...
metadata["status"] = "completed"
save_metadata(metadata)
# 如果中间崩溃，状态永远是 processing！

# ✅ 正确：使用事务式更新
try:
    update_status(job_id, TaskStatus.PROCESSING)
    # ... 编码 ...
    update_status(job_id, TaskStatus.COMPLETED)
except Exception as e:
    update_status(job_id, TaskStatus.FAILED, str(e))
```

#### 6. 清理时删除正在使用的任务

```python
# ❌ 错误：直接删除（可能删除正在处理的任务）
if completed_at < cutoff_date:
    shutil.rmtree(job_dir)

# ✅ 正确：检查锁文件
if completed_at < cutoff_date:
    if safe_delete_job(job_id):  # 尝试获取锁
        print(f"已删除: {job_id}")
    else:
        print(f"跳过（正在使用）: {job_id}")
```

#### 7. 磁盘空间不足未处理

```python
# ❌ 错误：未检查磁盘空间
def encode_video(job_id):
    ffmpeg.run(...)  # 可能因磁盘满而失败！

# ✅ 正确：提前检查
def encode_video(job_id):
    if not check_disk_space(min_free_gb=10):
        raise IOError("磁盘空间不足")

    try:
        ffmpeg.run(...)
    except IOError as e:
        if "No space left" in str(e):
            handle_disk_full_error(job_id, e)
```

#### 8. JSON 解析失败

```python
# ❌ 错误：未处理损坏的 JSON 文件
with open("metadata.json") as f:
    data = json.load(f)  # 文件损坏会抛异常！

# ✅ 正确：容错处理
try:
    with open("metadata.json") as f:
        data = json.load(f)
except json.JSONDecodeError:
    # 尝试从备份恢复
    backup_file = "metadata.json.backup"
    if Path(backup_file).exists():
        with open(backup_file) as f:
            data = json.load(f)
    else:
        raise ValueError("元数据文件损坏且无备份")
```

### 8.3 性能优化建议

| 场景 | 问题 | 解决方案 |
|------|------|----------|
| **列表查询慢** | 遍历所有目录读取元数据 | 维护轻量级索引（`metadata.db.json`） |
| **大文件传输慢** | 视频文件过大 | 使用流式传输（`StreamingResponse`） |
| **并发编码卡顿** | CPU/IO 资源耗尽 | 限制并发数（信号量或队列） |
| **日志文件过大** | 单文件数 GB | 滚动日志 + 压缩归档 |
| **CSV 生成慢** | 逐行写入 | 批量写入（缓冲区） |

### 8.4 安全性建议

| 威胁 | 防御措施 |
|------|----------|
| **路径遍历攻击** | 验证 job_id 格式（仅允许字母数字） |
| **枚举攻击** | 使用随机 ID + 访问 token |
| **竞态条件** | 使用文件锁 + 原子操作 |
| **磁盘填充攻击** | 限制任务数 + 磁盘配额 |
| **日志注入** | 结构化日志（JSON）+ 转义 |

```python
# 路径遍历防御
import re

def validate_job_id(job_id: str) -> bool:
    """验证 job_id 格式（仅允许字母数字）"""
    return bool(re.match(r"^[a-zA-Z0-9]{12}$", job_id))

def get_safe_job_dir(job_id: str) -> Path:
    """安全获取任务目录"""
    if not validate_job_id(job_id):
        raise ValueError(f"非法 job_id: {job_id}")

    prefix = job_id[:2]
    job_dir = JOBS_DIR / prefix / job_id

    # 确保路径在 JOBS_DIR 内（防止 ../ 攻击）
    if not job_dir.resolve().is_relative_to(JOBS_DIR.resolve()):
        raise ValueError(f"路径遍历攻击: {job_id}")

    return job_dir
```

---

## 总结

### 关键决策

| 决策点 | 推荐方案 | 理由 |
|--------|----------|------|
| **目录结构** | 两级分桶 | 平衡性能与复杂度 |
| **任务 ID** | nanoid (12 字符) | 短小、安全、碰撞概率低 |
| **状态管理** | metadata.json | 自包含、易于备份 |
| **原子性** | 临时文件 + rename | POSIX 原子性保证 |
| **并发控制** | fcntl.flock | 跨进程可靠 |
| **清理策略** | Cron 定时任务 | 独立进程、不影响应用 |
| **错误恢复** | 启动时检查 PID | 自动恢复中断任务 |

### 下一步行动

1. **Phase 0 验证**：使用小规模测试验证文件系统方案性能
2. **Phase 1 实现**：实现核心 TaskManager 类与 FastAPI 集成
3. **Phase 2 测试**：编写契约测试与并发场景测试
4. **Phase 3 优化**：根据性能测试结果优化索引与清理策略

---

**参考资源**:
- [nanoid 文档](https://github.com/puyuan/py-nanoid)
- [fcntl 文件锁](https://docs.python.org/3/library/fcntl.html)
- [POSIX rename 原子性](https://pubs.opengroup.org/onlinepubs/9699919799/functions/rename.html)
- [Pydantic 模型验证](https://docs.pydantic.dev/latest/)
