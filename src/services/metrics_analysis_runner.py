"""Metrics analysis runner - re-exports from application layer."""
from src.application.template_executor import TemplateExecutor, template_executor

metrics_analysis_runner = template_executor

__all__ = ["TemplateExecutor", "metrics_analysis_runner"]
