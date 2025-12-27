"""FFprobe operations."""
from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any, Dict, List, Optional


class FFProber:
    """FFprobe wrapper for video information extraction."""

    def __init__(self, ffprobe_path: str = "ffprobe"):
        self.ffprobe_path = ffprobe_path

    async def get_video_info(
        self, video_path: Path, input_format: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get video file information."""
        cmd = [
            self.ffprobe_path,
            "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            "-show_streams",
        ]
        if input_format:
            cmd.extend(["-f", input_format])
        cmd.append(str(video_path))

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                raise RuntimeError(f"ffprobe failed: {stderr.decode()}")

            info = json.loads(stdout.decode())

            video_stream = None
            for stream in info.get("streams", []):
                if stream.get("codec_type") == "video":
                    video_stream = stream
                    break

            if not video_stream:
                raise ValueError("No video stream found")

            format_info = info.get("format", {})

            fps = None
            if "r_frame_rate" in video_stream:
                num, den = map(int, video_stream["r_frame_rate"].split("/"))
                if den != 0:
                    fps = num / den

            return {
                "duration": float(format_info.get("duration", 0)),
                "width": int(video_stream.get("width", 0)),
                "height": int(video_stream.get("height", 0)),
                "fps": fps,
                "bitrate": int(format_info.get("bit_rate", 0)),
                "codec_name": video_stream.get("codec_name"),
                "nb_frames": (
                    int(video_stream.get("nb_frames"))
                    if str(video_stream.get("nb_frames", "")).isdigit()
                    else None
                ),
            }
        except Exception as e:
            raise RuntimeError(f"Failed to get video info: {str(e)}")

    async def probe_video_frames(
        self, video_path: Path, input_format: Optional[str] = None, timeout: int = 600
    ) -> List[Dict[str, Any]]:
        """Extract per-frame information using ffprobe."""
        cmd: List[str] = [
            self.ffprobe_path,
            "-v", "quiet",
            "-print_format", "json",
            "-select_streams", "v:0",
            "-show_frames",
            "-show_entries", "frame=pict_type,pkt_size,best_effort_timestamp_time,pkt_pts_time",
        ]
        if input_format:
            cmd.extend(["-f", input_format])
        cmd.append(str(video_path))

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout)

            if process.returncode != 0:
                raise RuntimeError(f"ffprobe failed: {stderr.decode()}")

            payload = json.loads(stdout.decode())
            frames = payload.get("frames", []) or []
            results: List[Dict[str, Any]] = []

            for idx, frame in enumerate(frames):
                pkt_size = frame.get("pkt_size")
                try:
                    size_val = int(pkt_size) if pkt_size is not None else 0
                except (TypeError, ValueError):
                    size_val = 0

                ts_val = frame.get("best_effort_timestamp_time")
                if ts_val is None:
                    ts_val = frame.get("pkt_pts_time")

                timestamp: Optional[float]
                try:
                    timestamp = float(ts_val) if ts_val is not None else None
                except (TypeError, ValueError):
                    timestamp = None

                results.append({
                    "index": idx,
                    "pict_type": frame.get("pict_type") or None,
                    "pkt_size": size_val,
                    "timestamp": timestamp,
                })

            return results
        except Exception as e:
            raise RuntimeError(f"Failed to probe frames: {str(e)}")
