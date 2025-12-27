"""Template API schemas."""
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

from src.domain.models.template import EncoderType, RateControl


class TemplateSidePayload(BaseModel):
    skip_encode: bool = False
    source_dir: str
    encoder_type: Optional[EncoderType] = None
    encoder_params: Optional[str] = None
    rate_control: Optional[RateControl] = None
    bitrate_points: List[float] = Field(default_factory=list)
    bitstream_dir: str


class CreateTemplateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    anchor: TemplateSidePayload
    test: TemplateSidePayload


class UpdateTemplateRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    anchor: Optional[TemplateSidePayload] = None
    test: Optional[TemplateSidePayload] = None


class TemplateResponse(BaseModel):
    template_id: str
    name: str
    description: Optional[str]
    template_type: str
    anchor: dict
    test: Optional[dict] = None
    anchor_computed: bool
    anchor_fingerprint: Optional[str]
    created_at: datetime
    updated_at: datetime


class CreateTemplateResponse(BaseModel):
    template_id: str
    status: str = "created"


class ValidateTemplateResponse(BaseModel):
    template_id: str
    source_exists: bool
    output_dir_writable: bool
    all_valid: bool


class TemplateListItem(BaseModel):
    template_id: str
    name: str
    description: Optional[str]
    created_at: datetime
    template_type: str
    anchor_source_dir: str
    anchor_bitstream_dir: str
    test_source_dir: Optional[str] = None
    test_bitstream_dir: Optional[str] = None
    anchor_computed: bool = False
