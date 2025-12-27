"""Encoding utilities - re-exports from application layer."""
from src.application.template_executor import SourceInfo

# Re-export commonly used functions
from src.infrastructure.ffmpeg.prober import FFProber
from src.config import settings

_prober = FFProber(settings.get_ffprobe_bin())


def now():
    """Get current time with timezone."""
    from datetime import datetime
    return datetime.now().astimezone()


async def collect_sources(source_dir: str):
    """Collect source video information from directory."""
    from src.application.template_executor import _collect_sources
    return await _collect_sources(source_dir)


__all__ = ["SourceInfo", "collect_sources", "now"]
