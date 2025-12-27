"""Template storage - re-exports from infrastructure layer."""
from src.infrastructure.persistence.template_repository import (
    TemplateRepository,
    template_repository as template_storage,
)

__all__ = ["TemplateRepository", "template_storage"]
