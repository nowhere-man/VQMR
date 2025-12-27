"""Template runner - re-exports from application layer."""
from src.application.template_executor import TemplateExecutor, template_executor

template_runner = template_executor

__all__ = ["TemplateExecutor", "template_runner"]
