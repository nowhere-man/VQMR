"""
API 端点实现 - 转码模板管理

提供模板创建、查询、更新、删除等 RESTful API
"""
from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from src.models_template import EncodingTemplateMetadata
from src.schemas_template import (
    CreateTemplateRequest,
    CreateTemplateResponse,
    TemplateListItem,
    TemplateResponse,
    UpdateTemplateRequest,
    ValidateTemplateResponse,
)
from src.services.template_encoder import template_encoder_service
from src.services.template_storage import template_storage

router = APIRouter(prefix="/api/templates", tags=["templates"])


class ExecuteTemplateRequest(BaseModel):
    """执行模板转码请求"""

    source_files: Optional[List[str]] = Field(
        None, description="可选的源文件列表，不提供则使用模板配置"
    )


class ExecuteTemplateResponse(BaseModel):
    """执行模板转码响应"""

    template_id: str = Field(..., description="模板 ID")
    template_name: str = Field(..., description="模板名称")
    total_files: int = Field(..., description="总文件数")
    successful: int = Field(..., description="成功转码数")
    failed: int = Field(..., description="失败数")
    results: List[dict] = Field(..., description="转码结果列表")
    errors: List[dict] = Field(..., description="错误列表")


@router.post(
    "",
    response_model=CreateTemplateResponse,
    status_code=201,
    summary="创建转码模板",
)
async def create_template(request: CreateTemplateRequest) -> CreateTemplateResponse:
    """
    创建新的转码模板

    - **name**: 模板名称
    - **encoder_type**: 编码器类型（ffmpeg/x264/x265/vvenc）
    - **encoder_params**: 编码参数字符串
    - **source_path**: 源视频路径或目录
    - **output_dir**: 输出目录
    - **metrics_report_dir**: 报告目录
    """
    # 生成模板 ID
    template_id = template_storage.generate_template_id()

    # 创建模板元数据
    metadata = EncodingTemplateMetadata(
        template_id=template_id,
        name=request.name,
        description=request.description,
        encoder_type=request.encoder_type,
        encoder_params=request.encoder_params,
        source_path=request.source_path,
        output_dir=request.output_dir,
        metrics_report_dir=request.metrics_report_dir,
        enable_metrics=request.enable_metrics,
        metrics_types=request.metrics_types,
        output_format=request.output_format,
        parallel_jobs=request.parallel_jobs,
    )

    # 创建模板
    try:
        template = template_storage.create_template(metadata)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return CreateTemplateResponse(
        template_id=template.template_id,
        name=template.name,
        created_at=template.metadata.created_at,
    )


@router.get(
    "/{template_id}",
    response_model=TemplateResponse,
    summary="获取模板详情",
)
async def get_template(template_id: str) -> TemplateResponse:
    """
    获取模板详情

    - **template_id**: 模板 ID
    """
    template = template_storage.get_template(template_id)

    if not template:
        raise HTTPException(status_code=404, detail=f"Template {template_id} not found")

    metadata = template.metadata

    return TemplateResponse(
        template_id=metadata.template_id,
        name=metadata.name,
        description=metadata.description,
        encoder_type=metadata.encoder_type,
        encoder_params=metadata.encoder_params,
        source_path=metadata.source_path,
        output_dir=metadata.output_dir,
        metrics_report_dir=metadata.metrics_report_dir,
        enable_metrics=metadata.enable_metrics,
        metrics_types=metadata.metrics_types,
        output_format=metadata.output_format,
        parallel_jobs=metadata.parallel_jobs,
        created_at=metadata.created_at,
        updated_at=metadata.updated_at,
    )


@router.get(
    "",
    response_model=List[TemplateListItem],
    summary="列出所有模板",
)
async def list_templates(
    encoder_type: Optional[str] = None,
    limit: Optional[int] = None,
) -> List[TemplateListItem]:
    """
    列出所有模板

    - **encoder_type**: 可选的编码器类型过滤
    - **limit**: 可选的数量限制
    """
    templates = template_storage.list_templates(encoder_type=encoder_type, limit=limit)

    return [
        TemplateListItem(
            template_id=t.metadata.template_id,
            name=t.metadata.name,
            description=t.metadata.description,
            encoder_type=t.metadata.encoder_type,
            created_at=t.metadata.created_at,
        )
        for t in templates
    ]


@router.put(
    "/{template_id}",
    response_model=TemplateResponse,
    summary="更新模板",
)
async def update_template(
    template_id: str, request: UpdateTemplateRequest
) -> TemplateResponse:
    """
    更新模板配置

    - **template_id**: 模板 ID
    - 其他字段为可选更新项
    """
    template = template_storage.get_template(template_id)

    if not template:
        raise HTTPException(status_code=404, detail=f"Template {template_id} not found")

    # 更新非空字段
    if request.name is not None:
        template.metadata.name = request.name
    if request.description is not None:
        template.metadata.description = request.description
    if request.encoder_type is not None:
        template.metadata.encoder_type = request.encoder_type
    if request.encoder_params is not None:
        template.metadata.encoder_params = request.encoder_params
    if request.source_path is not None:
        template.metadata.source_path = request.source_path
    if request.output_dir is not None:
        template.metadata.output_dir = request.output_dir
    if request.metrics_report_dir is not None:
        template.metadata.metrics_report_dir = request.metrics_report_dir
    if request.enable_metrics is not None:
        template.metadata.enable_metrics = request.enable_metrics
    if request.metrics_types is not None:
        template.metadata.metrics_types = request.metrics_types
    if request.output_format is not None:
        template.metadata.output_format = request.output_format
    if request.parallel_jobs is not None:
        template.metadata.parallel_jobs = request.parallel_jobs

    # 保存更新
    template_storage.update_template(template)

    metadata = template.metadata

    return TemplateResponse(
        template_id=metadata.template_id,
        name=metadata.name,
        description=metadata.description,
        encoder_type=metadata.encoder_type,
        encoder_params=metadata.encoder_params,
        source_path=metadata.source_path,
        output_dir=metadata.output_dir,
        metrics_report_dir=metadata.metrics_report_dir,
        enable_metrics=metadata.enable_metrics,
        metrics_types=metadata.metrics_types,
        output_format=metadata.output_format,
        parallel_jobs=metadata.parallel_jobs,
        created_at=metadata.created_at,
        updated_at=metadata.updated_at,
    )


@router.delete(
    "/{template_id}",
    status_code=204,
    summary="删除模板",
)
async def delete_template(template_id: str) -> None:
    """
    删除模板

    - **template_id**: 模板 ID
    """
    success = template_storage.delete_template(template_id)

    if not success:
        raise HTTPException(status_code=404, detail=f"Template {template_id} not found")


@router.get(
    "/{template_id}/validate",
    response_model=ValidateTemplateResponse,
    summary="验证模板路径",
)
async def validate_template(template_id: str) -> ValidateTemplateResponse:
    """
    验证模板配置的路径是否有效

    - **template_id**: 模板 ID
    """
    template = template_storage.get_template(template_id)

    if not template:
        raise HTTPException(status_code=404, detail=f"Template {template_id} not found")

    validation_results = template.validate_paths()

    all_valid = all(validation_results.values())

    return ValidateTemplateResponse(
        template_id=template_id,
        source_exists=validation_results["source_exists"],
        output_dir_writable=validation_results["output_dir_writable"],
        metrics_dir_writable=validation_results["metrics_dir_writable"],
        all_valid=all_valid,
    )


@router.post(
    "/{template_id}/execute",
    response_model=ExecuteTemplateResponse,
    summary="执行模板转码",
)
async def execute_template(
    template_id: str, request: ExecuteTemplateRequest
) -> ExecuteTemplateResponse:
    """
    使用模板执行视频转码

    - **template_id**: 模板 ID
    - **source_files**: 可选的源文件列表
    """
    template = template_storage.get_template(template_id)

    if not template:
        raise HTTPException(status_code=404, detail=f"Template {template_id} not found")

    # 解析源文件路径
    from pathlib import Path

    source_files = None
    if request.source_files:
        source_files = [Path(f) for f in request.source_files]

    # 执行转码
    try:
        result = await template_encoder_service.encode_with_template(
            template, source_files
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"转码失败: {str(e)}")

    return ExecuteTemplateResponse(**result)
