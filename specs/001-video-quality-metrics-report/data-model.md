# 数据模型设计：视频质量指标报告系统

**特性分支**: `001-video-quality-metrics-report`
**设计日期**: 2025-10-25
**状态**: Phase 1 设计

## 概述

本文档定义 VQMR 项目的核心数据模型，基于功能规格（spec.md）中的关键实体和需求。所有模型使用 Pydantic 实现类型安全和自动验证。

## 一、核心实体模型

### 1.1 EncodingTask（编码任务）

**描述**: 表示用户提交的单个编码作业

**属性**:

| 字段 | 类型 | 必需 | 描述 | 来源需求 |
|------|------|------|------|---------|
| `job_id` | `str` | ✅ | 任务唯一标识符（nanoid, 12 字符） | FR-029, FR-030 |
| `status` | `TaskStatus` | ✅ | 任务状态（枚举类型） | FR-029 |
| `encoder_path` | `Path` | ✅ | 编码器可执行文件的绝对路径 | FR-002, FR-003 |
| `created_at` | `datetime` | ✅ | 任务创建时间 | FR-029 |
| `updated_at` | `datetime` | ✅ | 任务最后更新时间 | FR-029 |
| `video_file` | `VideoFile` | ✅ | 输入视频配置 | FR-004, FR-005, FR-006 |
| `rate_control` | `RateControlConfig` | ✅ | 码控模式配置 | FR-008, FR-009, FR-012 |
| `progress` | `TaskProgress \| None` | ❌ | 任务进度信息（处理中时） | FR-029 |
| `error` | `str \| None` | ❌ | 错误消息（失败时） | FR-027 |

**状态枚举** (`TaskStatus`):

```python
from enum import Enum

class TaskStatus(str, Enum):
    QUEUED = "queued"           # 已排队
    PROCESSING = "processing"   # 处理中
    COMPLETED = "completed"     # 已完成
    FAILED = "failed"           # 失败
    CANCELLED = "cancelled"     # 已取消
```

**Pydantic 模型定义**:

```python
from pydantic import BaseModel, Field, validator
from pathlib import Path
from datetime import datetime
from typing import Optional

class EncodingTask(BaseModel):
    job_id: str = Field(..., min_length=12, max_length=12, description="任务 ID（nanoid）")
    status: TaskStatus = Field(default=TaskStatus.QUEUED, description="任务状态")
    encoder_path: Path = Field(..., description="编码器路径")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    video_file: VideoFile
    rate_control: RateControlConfig
    progress: Optional[TaskProgress] = None
    error: Optional[str] = None

    @validator('encoder_path')
    def validate_encoder_exists(cls, v):
        """验证编码器文件存在且可执行（FR-003）"""
        if not v.exists():
            raise ValueError(f"编码器文件不存在: {v}")
        if not v.is_file():
            raise ValueError(f"编码器路径不是文件: {v}")
        if not os.access(v, os.X_OK):
            raise ValueError(f"编码器文件不可执行: {v}")
        return v

    class Config:
        json_encoders = {
            Path: str,
            datetime: lambda v: v.isoformat()
        }
```

---

### 1.2 VideoFile（视频文件）

**描述**: 表示要编码的输入视频

**属性**:

| 字段 | 类型 | 必需 | 描述 | 来源需求 |
|------|------|------|------|---------|
| `file_path` | `Path` | ✅ | 视频文件的绝对路径 | FR-004, FR-007 |
| `format_type` | `VideoFormat` | ✅ | 格式类型（容器/原始 YUV） | FR-005, FR-006 |
| `yuv_metadata` | `YUVMetadata \| None` | ❌ | YUV 元数据（仅 YUV 格式需要） | FR-006 |

**格式枚举** (`VideoFormat`):

```python
class VideoFormat(str, Enum):
    CONTAINER = "container"  # MP4, FLV 等容器格式
    RAW_YUV = "raw_yuv"      # 原始 YUV 格式
```

**Pydantic 模型定义**:

```python
class VideoFile(BaseModel):
    file_path: Path = Field(..., description="视频文件路径")
    format_type: VideoFormat = Field(..., description="视频格式类型")
    yuv_metadata: Optional[YUVMetadata] = None

    @validator('file_path')
    def validate_video_exists(cls, v):
        """验证视频文件存在且可读（FR-007）"""
        if not v.exists():
            raise ValueError(f"视频文件不存在: {v}")
        if not v.is_file():
            raise ValueError(f"视频路径不是文件: {v}")
        if not os.access(v, os.R_OK):
            raise ValueError(f"视频文件不可读: {v}")
        return v

    @validator('yuv_metadata')
    def validate_yuv_metadata(cls, v, values):
        """YUV 格式时元数据必须提供（FR-006）"""
        if values.get('format_type') == VideoFormat.RAW_YUV and v is None:
            raise ValueError("RAW_YUV 格式必须提供 yuv_metadata")
        if values.get('format_type') == VideoFormat.CONTAINER and v is not None:
            raise ValueError("容器格式不应提供 yuv_metadata")
        return v
```

---

### 1.3 YUVMetadata（YUV 元数据）

**描述**: 原始 YUV 文件的必需元数据

**属性**:

| 字段 | 类型 | 必需 | 描述 | 来源需求 |
|------|------|------|------|---------|
| `resolution` | `Resolution` | ✅ | 分辨率（宽x高） | FR-006 |
| `pixel_format` | `str` | ✅ | 像素格式（如 yuv420p） | FR-006 |
| `frame_rate` | `float` | ✅ | 帧率（fps） | FR-006 |

**Pydantic 模型定义**:

```python
class Resolution(BaseModel):
    width: int = Field(..., gt=0, description="视频宽度")
    height: int = Field(..., gt=0, description="视频高度")

    def __str__(self):
        return f"{self.width}x{self.height}"

class YUVMetadata(BaseModel):
    resolution: Resolution
    pixel_format: str = Field(..., pattern=r"^yuv\d{3}p$", description="像素格式（如 yuv420p）")
    frame_rate: float = Field(..., gt=0, le=240, description="帧率（fps）")

    @validator('pixel_format')
    def validate_pixel_format(cls, v):
        """验证像素格式符合标准命名（假设）"""
        valid_formats = ["yuv420p", "yuv422p", "yuv444p", "yuv410p", "yuv411p"]
        if v not in valid_formats:
            raise ValueError(f"不支持的像素格式: {v}，有效值: {valid_formats}")
        return v
```

---

### 1.4 RateControlConfig（码控配置）

**描述**: 编码器码控模式配置

**属性**:

| 字段 | 类型 | 必需 | 描述 | 来源需求 |
|------|------|------|------|---------|
| `mode` | `RateControlMode` | ✅ | 码控模式（ABR/CRF） | FR-008, FR-009 |
| `values` | `list[int \| float]` | ✅ | 码控参数值列表 | FR-010, FR-011 |

**模式枚举** (`RateControlMode`):

```python
class RateControlMode(str, Enum):
    ABR = "abr"  # Average Bitrate (kbps)
    CRF = "crf"  # Constant Rate Factor
```

**Pydantic 模型定义**:

```python
class RateControlConfig(BaseModel):
    mode: RateControlMode
    values: list[int | float] = Field(..., min_items=1, max_items=10, description="码控参数值（至少 1 个，最多 10 个）")

    @validator('values')
    def validate_rate_values(cls, v, values):
        """验证码控参数值的有效性"""
        mode = values.get('mode')

        if mode == RateControlMode.ABR:
            # ABR 值必须为正整数（kbps）
            for val in v:
                if not isinstance(val, int) or val <= 0:
                    raise ValueError(f"ABR 值必须为正整数（kbps）: {val}")
                if val > 100000:  # 100 Mbps
                    raise ValueError(f"ABR 值过大: {val} kbps")

        elif mode == RateControlMode.CRF:
            # CRF 值范围 0-51（H.264/H.265）
            for val in v:
                if not (0 <= val <= 51):
                    raise ValueError(f"CRF 值必须在 0-51 之间: {val}")

        return v
```

---

### 1.5 QualityMetrics（质量指标）

**描述**: 编码输出的计算视频质量测量值

**属性**:

| 字段 | 类型 | 必需 | 描述 | 来源需求 |
|------|------|------|------|---------|
| `psnr_y` | `float` | ✅ | PSNR Y 分量（dB） | FR-014 |
| `psnr_u` | `float` | ✅ | PSNR U 分量（dB） | FR-014 |
| `psnr_v` | `float` | ✅ | PSNR V 分量（dB） | FR-014 |
| `psnr_avg` | `float` | ✅ | PSNR 平均值（dB） | FR-014 |
| `vmaf` | `float` | ✅ | VMAF 分数（0-100） | FR-015 |
| `ssim` | `float` | ✅ | SSIM 值（0-1） | FR-016 |
| `actual_bitrate` | `int` | ✅ | 实际码率（kbps） | FR-017 |
| `frames` | `list[FrameMetrics]` | ✅ | 逐帧指标（用于曲线图） | FR-022 |

**Pydantic 模型定义**:

```python
class FrameMetrics(BaseModel):
    frame_number: int = Field(..., ge=1, description="帧号")
    psnr_y: float = Field(..., description="PSNR Y 分量")
    vmaf: float = Field(..., ge=0, le=100, description="VMAF 分数")
    ssim: float = Field(..., ge=0, le=1, description="SSIM 值")

class QualityMetrics(BaseModel):
    psnr_y: float = Field(..., description="平均 PSNR Y 分量")
    psnr_u: float
    psnr_v: float
    psnr_avg: float
    vmaf: float = Field(..., ge=0, le=100)
    ssim: float = Field(..., ge=0, le=1)
    actual_bitrate: int = Field(..., gt=0, description="实际码率（kbps）")
    frames: list[FrameMetrics] = Field(default_factory=list, description="逐帧指标")

    @validator('psnr_avg')
    def validate_psnr_avg(cls, v, values):
        """验证 PSNR 平均值与分量一致性（可选）"""
        if 'psnr_y' in values and 'psnr_u' in values and 'psnr_v' in values:
            expected_avg = (values['psnr_y'] + values['psnr_u'] + values['psnr_v']) / 3
            if abs(v - expected_avg) > 0.1:  # 容差 0.1 dB
                raise ValueError(f"PSNR 平均值不一致: {v} vs 期望 {expected_avg:.2f}")
        return v
```

---

### 1.6 PerformanceMetrics（性能指标）

**描述**: 编码性能测量值

**属性**:

| 字段 | 类型 | 必需 | 描述 | 来源需求 |
|------|------|------|------|---------|
| `encoding_time` | `float` | ✅ | 总编码时间（秒） | FR-018 |
| `encoding_speed` | `float` | ✅ | 编码速度（fps 或倍数） | FR-019 |
| `cpu_utilization` | `float` | ✅ | CPU 利用率百分比 | FR-020 |
| `frame_latency` | `FrameLatencyStats` | ✅ | 逐帧延迟统计 | FR-021, FR-024 |

**Pydantic 模型定义**:

```python
class FrameLatencyStats(BaseModel):
    avg_ms: float = Field(..., description="平均逐帧延迟（毫秒）")
    min_ms: float = Field(..., description="最小延迟（毫秒）")
    max_ms: float = Field(..., description="最大延迟（毫秒）")

    @validator('avg_ms', 'min_ms', 'max_ms')
    def validate_positive(cls, v):
        if v < 0:
            raise ValueError(f"延迟值不能为负数: {v}")
        return v

class PerformanceMetrics(BaseModel):
    encoding_time: float = Field(..., gt=0, description="总编码时间（秒）")
    encoding_speed: float = Field(..., gt=0, description="编码速度（fps）")
    cpu_utilization: float = Field(..., ge=0, le=100, description="CPU 利用率百分比")
    frame_latency: FrameLatencyStats

    @validator('encoding_speed')
    def validate_speed_unit(cls, v, values):
        """编码速度单位验证（可选：转换为倍数）"""
        # 示例：如果 v > 1000，可能是 fps；否则是倍数
        return v
```

---

### 1.7 Report（报告）

**描述**: 可视化报告的数据结构

**属性**:

| 字段 | 类型 | 必需 | 描述 | 来源需求 |
|------|------|------|------|---------|
| `job_id` | `str` | ✅ | 关联的任务 ID | FR-025 |
| `video_metadata` | `VideoMetadata` | ✅ | 视频基本信息 | FR-025 |
| `results` | `list[EncodingResult]` | ✅ | 按码控参数分组的结果 | FR-025 |
| `created_at` | `datetime` | ✅ | 报告生成时间 | - |

**Pydantic 模型定义**:

```python
class VideoMetadata(BaseModel):
    resolution: str = Field(..., description="分辨率（如 1920x1080）")
    frame_rate: float = Field(..., description="帧率（fps）")
    codec: str = Field(..., description="编解码器（如 h264）")
    duration: float = Field(..., description="时长（秒）")

class EncodingResult(BaseModel):
    rate_control_param: int | float = Field(..., description="码控参数值（ABR kbps 或 CRF 值）")
    quality_metrics: QualityMetrics
    performance_metrics: PerformanceMetrics

class Report(BaseModel):
    job_id: str
    video_metadata: VideoMetadata
    results: list[EncodingResult] = Field(..., min_items=1, description="至少一个编码结果")
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
```

---

### 1.8 TaskProgress（任务进度）

**描述**: 任务处理进度信息

**属性**:

| 字段 | 类型 | 必需 | 描述 | 来源需求 |
|------|------|------|------|---------|
| `current_rate_param` | `int \| float \| None` | ❌ | 当前正在处理的码控参数 | FR-030 |
| `completed_params` | `list[int \| float]` | ✅ | 已完成的码控参数列表 | FR-030 |
| `total_tasks` | `int` | ✅ | 总任务数（码控参数个数） | FR-030 |
| `completed_tasks` | `int` | ✅ | 已完成任务数 | FR-030 |

**Pydantic 模型定义**:

```python
class TaskProgress(BaseModel):
    current_rate_param: Optional[int | float] = None
    completed_params: list[int | float] = Field(default_factory=list)
    total_tasks: int = Field(..., gt=0)
    completed_tasks: int = Field(default=0, ge=0)

    @validator('completed_tasks')
    def validate_progress(cls, v, values):
        """验证进度一致性"""
        if 'total_tasks' in values and v > values['total_tasks']:
            raise ValueError(f"已完成任务数 ({v}) 不能超过总任务数 ({values['total_tasks']})")
        return v

    @property
    def progress_percent(self) -> float:
        """计算进度百分比"""
        return (self.completed_tasks / self.total_tasks) * 100 if self.total_tasks > 0 else 0
```

---

## 二、关系与依赖

### 2.1 实体关系图（ER Diagram）

```
EncodingTask (1) ──────── (1) VideoFile
     │
     ├── (1) ──────── (1) RateControlConfig
     │
     ├── (0..1) ──── (1) TaskProgress
     │
     └── (1) ──────── (1) Report
                        │
                        ├── (1) ──── (1) VideoMetadata
                        │
                        └── (1..*) ── EncodingResult
                                       │
                                       ├── (1) ── QualityMetrics
                                       │           └── (0..*) FrameMetrics
                                       │
                                       └── (1) ── PerformanceMetrics
                                                   └── (1) FrameLatencyStats
```

### 2.2 状态转换图（State Machine）

```
      ┌─────────┐
      │ QUEUED  │ ◄─── 任务创建（POST /jobs）
      └────┬────┘
           │ 开始处理
           ▼
    ┌──────────────┐
    │  PROCESSING  │ ◄─── 编码/指标计算中
    └──┬───────┬───┘
       │       │
       │       └──────► ┌──────────┐
       │                │  FAILED  │ ◄─── 编码失败/崩溃/超时
       │                └──────────┘
       │ 所有任务完成
       ▼
  ┌───────────┐
  │ COMPLETED │ ◄─── 报告生成完成
  └───────────┘
       │
       │ 用户取消（可选）
       ▼
  ┌───────────┐
  │ CANCELLED │
  └───────────┘
```

---

## 三、验证规则与约束

### 3.1 跨字段验证

| 验证规则 | 实体 | 描述 | 来源需求 |
|---------|------|------|---------|
| YUV 元数据一致性 | `VideoFile` | `format_type=RAW_YUV` 时 `yuv_metadata` 必须提供 | FR-006 |
| 码控模式互斥 | `RateControlConfig` | 一次只能激活一种模式（ABR 或 CRF） | FR-012 |
| 进度一致性 | `TaskProgress` | `completed_tasks` ≤ `total_tasks` | FR-030 |
| PSNR 平均值 | `QualityMetrics` | `psnr_avg` 应接近 `(psnr_y + psnr_u + psnr_v) / 3` | FR-014 |

### 3.2 业务规则

1. **文件路径验证** (FR-003, FR-007):
   - 编码器路径必须存在、可执行
   - 视频文件路径必须存在、可读

2. **码控参数范围** (FR-008, FR-009):
   - ABR: 1 - 100000 kbps
   - CRF: 0 - 51

3. **指标值范围** (FR-014, FR-015, FR-016):
   - VMAF: 0 - 100
   - SSIM: 0 - 1
   - PSNR: 通常 20-50 dB（无严格限制）

4. **性能指标** (FR-020):
   - CPU 利用率: 0 - 100%
   - 编码时间: > 0 秒

---

## 四、数据持久化格式

### 4.1 metadata.json 示例

```json
{
  "job_id": "abc123def456",
  "status": "completed",
  "encoder_path": "/usr/bin/x264",
  "created_at": "2025-10-25T10:30:00Z",
  "updated_at": "2025-10-25T10:45:00Z",
  "video_file": {
    "file_path": "/path/to/input.mp4",
    "format_type": "container",
    "yuv_metadata": null
  },
  "rate_control": {
    "mode": "abr",
    "values": [500, 1000, 2000]
  },
  "progress": {
    "current_rate_param": null,
    "completed_params": [500, 1000, 2000],
    "total_tasks": 3,
    "completed_tasks": 3
  },
  "error": null
}
```

### 4.2 psnr.json 示例

```json
{
  "psnr_y": 42.35,
  "psnr_u": 45.12,
  "psnr_v": 44.87,
  "psnr_avg": 44.11,
  "vmaf": 85.67,
  "ssim": 0.9823,
  "actual_bitrate": 1987,
  "frames": [
    {"frame_number": 1, "psnr_y": 43.2, "vmaf": 86.5, "ssim": 0.984},
    {"frame_number": 2, "psnr_y": 41.8, "vmaf": 84.3, "ssim": 0.981}
  ]
}
```

---

## 五、Pydantic 配置总结

### 5.1 全局配置

```python
from pydantic import BaseConfig

class GlobalConfig(BaseConfig):
    # 允许任意类型（如 Path）
    arbitrary_types_allowed = True

    # JSON 编码器
    json_encoders = {
        Path: str,
        datetime: lambda v: v.isoformat()
    }

    # 验证赋值
    validate_assignment = True

    # 使用枚举值
    use_enum_values = True
```

### 5.2 验证模式

| 验证器 | 用途 | 示例 |
|--------|------|------|
| `@validator` | 字段级验证 | 验证文件存在 |
| `@root_validator` | 跨字段验证 | 验证 YUV 元数据一致性 |
| `Field(...)` 约束 | 内置验证 | `min_items=1`, `gt=0` |

---

## 六、与需求映射

### 6.1 功能需求覆盖

| 功能需求 | 数据模型支持 |
|---------|-------------|
| FR-001 ~ FR-007 | `EncodingTask`, `VideoFile`, `YUVMetadata` |
| FR-008 ~ FR-012 | `RateControlConfig`, `RateControlMode` |
| FR-013 ~ FR-019 | `QualityMetrics`, `PerformanceMetrics` |
| FR-020 ~ FR-021 | `PerformanceMetrics`, `FrameLatencyStats` |
| FR-022 ~ FR-026 | `Report`, `EncodingResult`, `FrameMetrics` |
| FR-027 ~ FR-030 | `EncodingTask.status`, `TaskProgress`, `EncodingTask.error` |

### 6.2 成功标准覆盖

| 成功标准 | 数据模型支持 |
|---------|-------------|
| SC-001 ~ SC-004 | `EncodingTask` 状态管理 |
| SC-005 | `QualityMetrics` 验证器（容差检查） |
| SC-006 | `Report.results` 多参数对比 |
| SC-009 | `EncodingTask` 文件路径验证器 |
| SC-010 | `Report.created_at` 时间戳 |

---

## 七、最佳实践

### 7.1 类型安全
- ✅ 使用 Pydantic `Field` 约束（`gt`, `ge`, `min_items` 等）
- ✅ 使用枚举类型（`TaskStatus`, `RateControlMode`, `VideoFormat`）
- ✅ 使用 `Path` 类型而非 `str`（自动路径规范化）

### 7.2 验证
- ✅ 自定义验证器验证业务规则（文件存在性、参数范围）
- ✅ 跨字段验证使用 `@root_validator`
- ✅ 验证错误返回清晰消息（符合 FR-027）

### 7.3 序列化
- ✅ 配置 `json_encoders` 处理特殊类型（`Path`, `datetime`）
- ✅ 使用 `model.dict()` 生成 JSON 友好字典
- ✅ 使用 `model.json()` 直接序列化为 JSON 字符串

### 7.4 文档
- ✅ 所有字段提供 `description`（自动生成 OpenAPI 文档）
- ✅ 使用类型提示（IDE 自动补全）
- ✅ 中文描述符合宪法要求

---

## 八、下一步

- [ ] 实现数据模型（`backend/src/models/`）
- [ ] 编写模型单元测试（`backend/tests/unit/test_models.py`）
- [ ] 生成 OpenAPI schema（`/docs`）
- [ ] 集成到 FastAPI 路由（`backend/src/api/`）

---

**设计完成日期**: 2025-10-25
**审查状态**: 待 Phase 1 完成后验证
