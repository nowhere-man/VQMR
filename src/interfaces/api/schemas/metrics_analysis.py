"""Metrics analysis API schemas."""
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

from src.domain.models.template import EncoderType, RateControl


class MetricsTemplatePayload(BaseModel):
    skip_encode: bool = False
    source_dir: str
    encoder_type: Optional[EncoderType] = None
    encoder_params: Optional[str] = None
    rate_control: Optional[RateControl] = None
    bitrate_points: List[float] = Field(default_factory=list)
    bitstream_dir: str


class CreateMetricsTemplateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    config: MetricsTemplatePayload


class UpdateMetricsTemplateRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    config: Optional[MetricsTemplatePayload] = None


class MetricsTemplateResponse(BaseModel):
    template_id: str
    name: str
    description: Optional[str]
    config: dict
    created_at: datetime
    updated_at: datetime
    template_type: str = "metrics_analysis"


class MetricsTemplateListItem(BaseModel):
    template_id: str
    name: str
    description: Optional[str]
    created_at: datetime
    source_dir: str
    bitstream_dir: str
    template_type: str = "metrics_analysis"


class ValidateMetricsTemplateResponse(BaseModel):
    template_id: str
    source_exists: bool
    output_dir_writable: bool
    all_valid: bool
