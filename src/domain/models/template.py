"""Template domain models."""
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator


class EncoderType(str, Enum):
    FFMPEG = "ffmpeg"
    X264 = "x264"
    X265 = "x265"
    VVENC = "vvenc"


class TemplateType(str, Enum):
    COMPARISON = "comparison"
    METRICS_ANALYSIS = "metrics_analysis"


class RateControl(str, Enum):
    CRF = "crf"
    ABR = "abr"


class TemplateSideConfig(BaseModel):
    """Anchor / Test side configuration."""

    skip_encode: bool = False
    source_dir: str
    encoder_type: Optional[EncoderType] = None
    encoder_params: Optional[str] = None
    rate_control: Optional[RateControl] = None
    bitrate_points: List[float] = Field(default_factory=list)
    bitstream_dir: str

    model_config = ConfigDict(extra="ignore")

    @model_validator(mode="after")
    def validate_fields(self) -> "TemplateSideConfig":
        ctx = getattr(self, "__pydantic_context__", {}) or {}
        skip_path_check = ctx.get("skip_path_check")
        if not self.source_dir.strip():
            raise ValueError("source_dir cannot be empty")
        if not skip_path_check and not Path(self.source_dir).is_dir():
            raise ValueError(f"Source directory does not exist: {self.source_dir}")
        if not self.bitstream_dir.strip():
            raise ValueError("bitstream_dir cannot be empty")

        if not self.skip_encode:
            if not self.encoder_type:
                raise ValueError("encoder_type required when not skipping encode")
            if not self.encoder_params or not self.encoder_params.strip():
                raise ValueError("encoder_params required when not skipping encode")
            if not self.rate_control:
                raise ValueError("rate_control required when not skipping encode")
            if not self.bitrate_points:
                raise ValueError("bitrate_points required when not skipping encode")
        return self


class EncodingTemplateMetadata(BaseModel):
    """Template metadata (persisted)."""

    template_id: str
    name: str
    description: Optional[str] = None

    template_type: TemplateType = TemplateType.COMPARISON

    anchor: TemplateSideConfig
    test: Optional[TemplateSideConfig] = None

    anchor_computed: bool = False
    anchor_fingerprint: Optional[str] = None

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = ConfigDict(
        extra="ignore",
        json_encoders={datetime: lambda v: v.isoformat()},
    )

    @model_validator(mode="after")
    def validate_by_type(self) -> "EncodingTemplateMetadata":
        if self.template_type == TemplateType.COMPARISON:
            if self.test is None:
                raise ValueError("Comparison template requires Test config")
        else:
            self.test = None
            self.anchor_computed = False
            self.anchor_fingerprint = None
        return self


class EncodingTemplate(BaseModel):
    """Template object (includes directory)."""

    metadata: EncodingTemplateMetadata
    template_dir: Path

    model_config = ConfigDict(arbitrary_types_allowed=True)

    @property
    def template_id(self) -> str:
        return self.metadata.template_id

    @property
    def name(self) -> str:
        return self.metadata.name

    def get_metadata_path(self) -> Path:
        return self.template_dir / "template.json"
