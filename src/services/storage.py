"""Job storage - re-exports from infrastructure layer."""
from src.infrastructure.persistence.job_repository import (
    JobRepository,
    job_repository as job_storage,
)

generate_job_id = job_storage.generate_job_id

__all__ = ["JobRepository", "job_storage", "generate_job_id"]
