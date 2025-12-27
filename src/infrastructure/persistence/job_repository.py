"""Job repository - JSON file persistence."""
import json
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from nanoid import generate

from src.config import settings
from src.domain.models.job import Job, JobMetadata, JobStatus


class JobRepository:
    """Job storage repository."""

    def __init__(self, root_dir: Optional[Path] = None):
        self.root_dir = (root_dir or settings.jobs_root_dir).resolve()
        self.root_dir.mkdir(parents=True, exist_ok=True)

    def create_job(self, metadata: JobMetadata) -> Job:
        """Create new job."""
        job_dir = self.root_dir / metadata.job_id

        if job_dir.exists():
            raise ValueError(f"Job {metadata.job_id} already exists")

        job_dir.mkdir(parents=True, exist_ok=True)
        job = Job(metadata=metadata, job_dir=job_dir)
        self._save_metadata(job)

        return job

    def get_job(self, job_id: str) -> Optional[Job]:
        """Get job by ID."""
        job_dir = self.root_dir / job_id

        if not job_dir.exists():
            return None

        metadata_path = job_dir / "metadata.json"
        if not metadata_path.exists():
            return None

        try:
            with open(metadata_path, "r", encoding="utf-8") as f:
                metadata_dict = json.load(f)
                metadata = JobMetadata(**metadata_dict)
                return Job(metadata=metadata, job_dir=job_dir)
        except Exception:
            return None

    def update_job(self, job: Job) -> None:
        """Update job metadata."""
        job.metadata.updated_at = datetime.utcnow()
        self._save_metadata(job)

    def list_jobs(
        self,
        status: Optional[JobStatus] = None,
        limit: Optional[int] = None,
    ) -> List[Job]:
        """List all jobs."""
        jobs: List[Job] = []

        if not self.root_dir.exists():
            return jobs

        for job_dir in self.root_dir.iterdir():
            if not job_dir.is_dir():
                continue

            metadata_path = job_dir / "metadata.json"
            if not metadata_path.exists():
                continue

            try:
                with open(metadata_path, "r", encoding="utf-8") as f:
                    metadata_dict = json.load(f)
                    metadata = JobMetadata(**metadata_dict)

                    if status and metadata.status != status:
                        continue

                    jobs.append(Job(metadata=metadata, job_dir=job_dir))
            except Exception:
                continue

        jobs.sort(key=lambda j: j.metadata.created_at, reverse=True)

        if limit:
            jobs = jobs[:limit]

        return jobs

    def delete_job(self, job_id: str) -> bool:
        """Delete job and all files."""
        job_dir = self.root_dir / job_id

        if not job_dir.exists():
            return False

        try:
            import shutil
            shutil.rmtree(job_dir)
            return True
        except Exception:
            return False

    def generate_job_id(self) -> str:
        """Generate unique job ID."""
        return generate(size=12)

    def _save_metadata(self, job: Job) -> None:
        """Save job metadata to JSON file."""
        metadata_path = job.get_metadata_path()

        with open(metadata_path, "w", encoding="utf-8") as f:
            metadata_dict = job.metadata.model_dump(mode="json")
            json.dump(metadata_dict, f, ensure_ascii=False, indent=2)


# Global singleton
job_repository = JobRepository()
