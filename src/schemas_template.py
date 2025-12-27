"""Template schemas module - backward compatibility layer."""
from src.interfaces.api.schemas.template import (
    CreateTemplateRequest,
    CreateTemplateResponse,
    TemplateListItem,
    TemplateResponse,
    TemplateSidePayload,
    UpdateTemplateRequest,
    ValidateTemplateResponse,
)

__all__ = [
    "CreateTemplateRequest",
    "CreateTemplateResponse",
    "TemplateListItem",
    "TemplateResponse",
    "TemplateSidePayload",
    "UpdateTemplateRequest",
    "ValidateTemplateResponse",
]
