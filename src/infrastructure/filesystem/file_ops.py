"""File operations infrastructure."""
from pathlib import Path

from src.domain.models.metrics import VideoInfo


def save_uploaded_file(file_content: bytes, destination: Path) -> None:
    """Save uploaded file to specified path."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    with open(destination, "wb") as f:
        f.write(file_content)


def extract_video_info(file_path: Path) -> VideoInfo:
    """Extract basic video file info (filename, size)."""
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    file_stat = file_path.stat()
    return VideoInfo(
        filename=file_path.name,
        size_bytes=file_stat.st_size,
        duration=None,
        width=None,
        height=None,
        fps=None,
        bitrate=None,
    )


def dir_exists(path: str) -> bool:
    """Check if directory exists."""
    return Path(path).is_dir()


def dir_writable(path: str) -> bool:
    """Check if directory is writable (creates if not exists)."""
    p = Path(path)
    try:
        p.mkdir(parents=True, exist_ok=True)
        test = p / ".writetest"
        test.write_text("ok")
        test.unlink()
        return True
    except Exception:
        return False
