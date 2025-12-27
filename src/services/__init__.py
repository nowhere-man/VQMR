"""Services module - backward compatibility layer."""
from src.infrastructure.persistence.job_repository import job_repository as job_storage
from src.infrastructure.persistence.template_repository import template_repository as template_storage
from src.application.job_processor import task_processor

__all__ = [
    "job_storage",
    "task_processor",
    "template_storage",
]
