"""
转码模板数据模型定义

定义转码模板相关的数据结构：EncodingTemplate、EncoderType 等
"""
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class EncoderType(str, Enum):
    """编码器类型枚举"""

    FFMPEG = "ffmpeg"  # FFmpeg 编码器
    X264 = "x264"  # x264 编码器
    X265 = "x265"  # x265 编码器
    VVENC = "vvenc"  # VVenC (VVC) 编码器


class EncodingTemplateMetadata(BaseModel):
    """转码模板元数据（持久化到 JSON）"""

    template_id: str = Field(..., description="模板 ID (nanoid 12字符)")
    name: str = Field(..., min_length=1, max_length=100, description="模板名称")
    description: Optional[str] = Field(None, max_length=500, description="模板描述")

    # 编码器配置
    encoder_type: EncoderType = Field(..., description="编码器类型")
    encoder_params: str = Field(
        ..., min_length=1, max_length=2000, description="编码参数（字符串格式）"
    )

    # 路径配置
    source_path: str = Field(
        ..., min_length=1, description="源视频路径或目录（支持通配符）"
    )
    output_dir: str = Field(..., min_length=1, description="转码后视频输出目录")
    metrics_report_dir: str = Field(..., min_length=1, description="metrics 报告保存目录")

    # 额外配置项
    enable_metrics: bool = Field(default=True, description="是否启用质量指标计算")
    metrics_types: list[str] = Field(
        default=["psnr", "ssim", "vmaf"], description="要计算的指标类型"
    )
    output_format: str = Field(default="mp4", description="输出视频格式")
    parallel_jobs: int = Field(
        default=1, ge=1, le=16, description="并行任务数（1-16）"
    )

    # 时间戳
    created_at: datetime = Field(default_factory=datetime.utcnow, description="创建时间")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="更新时间")

    @field_validator("metrics_types")
    @classmethod
    def validate_metrics_types(cls, v: list[str]) -> list[str]:
        """验证指标类型的有效性"""
        valid_types = {"psnr", "ssim", "vmaf"}
        invalid = set(v) - valid_types
        if invalid:
            raise ValueError(
                f"无效的指标类型: {invalid}. 有效值: {valid_types}"
            )
        return v

    @field_validator("source_path", "output_dir", "metrics_report_dir")
    @classmethod
    def validate_path_not_empty(cls, v: str) -> str:
        """验证路径不为空"""
        if not v.strip():
            raise ValueError("路径不能为空或仅包含空白字符")
        return v.strip()

    model_config = ConfigDict(
        json_encoders={
            datetime: lambda v: v.isoformat(),
        }
    )


class EncodingTemplate(BaseModel):
    """转码模板对象（内存中使用，包含文件路径）"""

    metadata: EncodingTemplateMetadata = Field(..., description="模板元数据")
    template_dir: Path = Field(..., description="模板目录路径")

    @property
    def template_id(self) -> str:
        """模板 ID"""
        return self.metadata.template_id

    @property
    def name(self) -> str:
        """模板名称"""
        return self.metadata.name

    def get_metadata_path(self) -> Path:
        """获取元数据文件路径"""
        return self.template_dir / "template.json"

    def validate_paths(self) -> dict[str, bool]:
        """
        验证配置的路径是否有效

        Returns:
            包含各路径验证结果的字典
        """
        results = {
            "source_exists": Path(self.metadata.source_path).exists(),
            "output_dir_writable": self._check_dir_writable(self.metadata.output_dir),
            "metrics_dir_writable": self._check_dir_writable(
                self.metadata.metrics_report_dir
            ),
        }
        return results

    def _check_dir_writable(self, dir_path: str) -> bool:
        """检查目录是否可写"""
        path = Path(dir_path)
        if not path.exists():
            try:
                path.mkdir(parents=True, exist_ok=True)
                return True
            except Exception:
                return False
        return path.is_dir() and path.stat().st_mode & 0o200

    model_config = ConfigDict(arbitrary_types_allowed=True)
