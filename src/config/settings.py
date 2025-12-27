"""
Application settings.

Centralizes configuration using Pydantic BaseSettings. This keeps defaults
in one place and allows overriding via environment variables.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration."""

    # Server
    host: str = "0.0.0.0"
    port: int = 8080
    reports_port: int = 8079  # Streamlit port

    # Storage
    jobs_root_dir: Path = Path("./jobs")
    templates_root_dir: Path = Path("./templates")

    # FFmpeg
    ffmpeg_path: Optional[str] = None
    ffmpeg_timeout: int = 600

    # Logging
    log_level: str = "INFO"

    model_config = SettingsConfigDict(
        env_prefix="VMA_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    def get_ffmpeg_bin(self) -> str:
        """Return ffmpeg binary path (uses custom path if configured)."""
        if self.ffmpeg_path:
            return str(Path(self.ffmpeg_path) / "ffmpeg")
        return "ffmpeg"

    def get_ffprobe_bin(self) -> str:
        """Return ffprobe binary path (uses custom path if configured)."""
        if self.ffmpeg_path:
            return str(Path(self.ffmpeg_path) / "ffprobe")
        return "ffprobe"


# Singleton instance
settings = Settings()
