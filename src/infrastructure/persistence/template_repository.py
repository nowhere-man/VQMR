"""Template repository - JSON file persistence."""
import json
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from nanoid import generate

from src.config import settings
from src.domain.models.template import (
    EncodingTemplate,
    EncodingTemplateMetadata,
    TemplateType,
)


class TemplateRepository:
    """Template storage repository."""

    def __init__(self, root_dir: Optional[Path] = None):
        self.root_dir = root_dir or settings.templates_root_dir
        self.root_dir.mkdir(parents=True, exist_ok=True)

    def create_template(self, metadata: EncodingTemplateMetadata) -> EncodingTemplate:
        """Create new template."""
        template_dir = self.root_dir / metadata.template_id

        if template_dir.exists():
            raise ValueError(f"Template {metadata.template_id} already exists")

        template_dir.mkdir(parents=True, exist_ok=True)
        template = EncodingTemplate(metadata=metadata, template_dir=template_dir)
        self._save_metadata(template)

        return template

    def get_template(self, template_id: str) -> Optional[EncodingTemplate]:
        """Get template by ID."""
        template_dir = self.root_dir / template_id

        if not template_dir.exists():
            return None

        metadata_path = template_dir / "template.json"
        if not metadata_path.exists():
            return None

        try:
            with open(metadata_path, "r", encoding="utf-8") as f:
                metadata_dict = json.load(f)
                metadata = EncodingTemplateMetadata.model_validate(
                    metadata_dict, context={"skip_path_check": True}
                )
                return EncodingTemplate(metadata=metadata, template_dir=template_dir)
        except Exception:
            return None

    def update_template(self, template: EncodingTemplate) -> None:
        """Update template metadata."""
        template.metadata.updated_at = datetime.utcnow()
        self._save_metadata(template)

    def list_templates(
        self,
        limit: Optional[int] = None,
        template_type: Optional[TemplateType] = None,
    ) -> List[EncodingTemplate]:
        """List all templates."""
        templates: List[EncodingTemplate] = []

        if not self.root_dir.exists():
            return templates

        for template_dir in self.root_dir.iterdir():
            if not template_dir.is_dir():
                continue

            metadata_path = template_dir / "template.json"
            if not metadata_path.exists():
                continue

            try:
                with open(metadata_path, "r", encoding="utf-8") as f:
                    metadata_dict = json.load(f)
                    metadata = EncodingTemplateMetadata(**metadata_dict)

                    if template_type is None or metadata.template_type == template_type:
                        templates.append(
                            EncodingTemplate(metadata=metadata, template_dir=template_dir)
                        )
            except Exception:
                continue

        templates.sort(key=lambda t: t.metadata.created_at, reverse=True)

        if limit:
            templates = templates[:limit]

        return templates

    def delete_template(self, template_id: str) -> bool:
        """Delete template and all files."""
        template_dir = self.root_dir / template_id

        if not template_dir.exists():
            return False

        try:
            import shutil
            shutil.rmtree(template_dir)
            return True
        except Exception:
            return False

    def generate_template_id(self) -> str:
        """Generate unique template ID."""
        return generate(size=12)

    def _save_metadata(self, template: EncodingTemplate) -> None:
        """Save template metadata to JSON file."""
        metadata_path = template.get_metadata_path()

        with open(metadata_path, "w", encoding="utf-8") as f:
            metadata_dict = template.metadata.model_dump(mode="json")
            json.dump(metadata_dict, f, ensure_ascii=False, indent=2)


# Global singleton
template_repository = TemplateRepository()
