"""
转码模板 API Schema 定义

定义转码模板相关的请求和响应模型
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from src.models_template import EncoderType


class CreateTemplateRequest(BaseModel):
    """创建模板请求"""

    name: str = Field(..., min_length=1, max_length=100, description="模板名称")
    description: Optional[str] = Field(None, max_length=500, description="模板描述")
    encoder_type: EncoderType = Field(..., description="编码器类型")
    encoder_params: str = Field(
        ..., min_length=1, max_length=2000, description="编码参数"
    )
    source_path: str = Field(..., min_length=1, description="源视频路径或目录")
    output_dir: str = Field(..., min_length=1, description="输出目录")
    metrics_report_dir: str = Field(..., min_length=1, description="报告目录")
    enable_metrics: bool = Field(default=True, description="是否启用质量指标计算")
    metrics_types: list[str] = Field(
        default=["psnr", "ssim", "vmaf"], description="要计算的指标类型"
    )
    output_format: str = Field(default="mp4", description="输出视频格式")
    parallel_jobs: int = Field(
        default=1, ge=1, le=16, description="并行任务数（1-16）"
    )


class UpdateTemplateRequest(BaseModel):
    """更新模板请求"""

    name: Optional[str] = Field(None, min_length=1, max_length=100, description="模板名称")
    description: Optional[str] = Field(None, max_length=500, description="模板描述")
    encoder_type: Optional[EncoderType] = Field(None, description="编码器类型")
    encoder_params: Optional[str] = Field(
        None, min_length=1, max_length=2000, description="编码参数"
    )
    source_path: Optional[str] = Field(None, min_length=1, description="源视频路径或目录")
    output_dir: Optional[str] = Field(None, min_length=1, description="输出目录")
    metrics_report_dir: Optional[str] = Field(None, min_length=1, description="报告目录")
    enable_metrics: Optional[bool] = Field(None, description="是否启用质量指标计算")
    metrics_types: Optional[list[str]] = Field(None, description="要计算的指标类型")
    output_format: Optional[str] = Field(None, description="输出视频格式")
    parallel_jobs: Optional[int] = Field(
        None, ge=1, le=16, description="并行任务数（1-16）"
    )


class TemplateResponse(BaseModel):
    """模板响应"""

    template_id: str = Field(..., description="模板 ID")
    name: str = Field(..., description="模板名称")
    description: Optional[str] = Field(None, description="模板描述")
    encoder_type: EncoderType = Field(..., description="编码器类型")
    encoder_params: str = Field(..., description="编码参数")
    source_path: str = Field(..., description="源视频路径或目录")
    output_dir: str = Field(..., description="输出目录")
    metrics_report_dir: str = Field(..., description="报告目录")
    enable_metrics: bool = Field(..., description="是否启用质量指标计算")
    metrics_types: list[str] = Field(..., description="要计算的指标类型")
    output_format: str = Field(..., description="输出视频格式")
    parallel_jobs: int = Field(..., description="并行任务数")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")


class TemplateListItem(BaseModel):
    """模板列表项"""

    template_id: str = Field(..., description="模板 ID")
    name: str = Field(..., description="模板名称")
    description: Optional[str] = Field(None, description="模板描述")
    encoder_type: EncoderType = Field(..., description="编码器类型")
    created_at: datetime = Field(..., description="创建时间")


class CreateTemplateResponse(BaseModel):
    """创建模板响应"""

    template_id: str = Field(..., description="模板 ID")
    name: str = Field(..., description="模板名称")
    created_at: datetime = Field(..., description="创建时间")


class ValidateTemplateResponse(BaseModel):
    """验证模板路径响应"""

    template_id: str = Field(..., description="模板 ID")
    source_exists: bool = Field(..., description="源路径是否存在")
    output_dir_writable: bool = Field(..., description="输出目录是否可写")
    metrics_dir_writable: bool = Field(..., description="报告目录是否可写")
    all_valid: bool = Field(..., description="所有路径是否都有效")
