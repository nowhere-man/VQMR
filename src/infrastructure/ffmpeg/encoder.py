"""FFmpeg encoding operations."""
from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from src.infrastructure.ffmpeg.runner import run_ffmpeg_command


class FFEncoder:
    """FFmpeg encoder wrapper."""

    def __init__(self, ffmpeg_path: str = "ffmpeg", timeout: int = 600):
        self.ffmpeg_path = ffmpeg_path
        self.timeout = timeout

    async def encode_video(
        self,
        input_path: Path,
        output_path: Path,
        preset: str = "medium",
        crf: int = 23,
        add_command_callback=None,
        update_status_callback=None,
        command_type: str = "encode",
        source_file: Optional[str] = None,
    ) -> None:
        """Encode video with fixed preset (single file mode)."""
        cmd = [
            self.ffmpeg_path,
            "-i", str(input_path),
            "-c:v", "libx264",
            "-preset", preset,
            "-crf", str(crf),
            "-c:a", "copy",
            str(output_path),
        ]

        await run_ffmpeg_command(
            cmd=cmd,
            timeout=self.timeout,
            add_command_callback=add_command_callback,
            update_status_callback=update_status_callback,
            command_type=command_type,
            source_file=source_file or str(input_path),
            on_success=lambda: None,
            error_prefix="Encoding failed",
        )

    async def decode_to_yuv420p(
        self,
        input_path: Path,
        output_path: Path,
        input_format: Optional[str] = None,
        input_width: Optional[int] = None,
        input_height: Optional[int] = None,
        input_fps: Optional[float] = None,
        input_pix_fmt: str = "yuv420p",
        scale_width: Optional[int] = None,
        scale_height: Optional[int] = None,
        add_command_callback=None,
        update_status_callback=None,
        command_type: str = "ffmpeg_decode",
        source_file: Optional[str] = None,
    ) -> None:
        """Decode input video to yuv420p rawvideo."""
        cmd: List[str] = [self.ffmpeg_path, "-y"]

        if input_width is not None and input_height is not None:
            cmd.extend(["-f", "rawvideo", "-pix_fmt", input_pix_fmt, "-s", f"{input_width}x{input_height}"])
            if input_fps is not None:
                cmd.extend(["-r", str(input_fps)])
            cmd.extend(["-i", str(input_path)])
        else:
            if input_format:
                cmd.extend(["-f", input_format])
            cmd.extend(["-i", str(input_path)])

        vf_parts: List[str] = []
        if scale_width is not None and scale_height is not None:
            vf_parts.append(f"scale={scale_width}:{scale_height}")
        vf_parts.append("format=yuv420p")

        cmd.extend(["-an", "-sn", "-vf", ",".join(vf_parts)])
        cmd.extend(["-f", "rawvideo", "-pix_fmt", "yuv420p", str(output_path)])

        await run_ffmpeg_command(
            cmd=cmd,
            timeout=self.timeout,
            add_command_callback=add_command_callback,
            update_status_callback=update_status_callback,
            command_type=command_type or "ffmpeg_decode",
            source_file=source_file or str(input_path),
            on_success=lambda: None,
            error_prefix="Decode to yuv failed",
            timeout_message="Decode to yuv timed out",
        )
