"""FFmpeg service - re-exports from infrastructure layer."""
from src.infrastructure.ffmpeg.encoder import FFEncoder
from src.infrastructure.ffmpeg.prober import FFProber
from src.infrastructure.ffmpeg.metrics_calculator import MetricsCalculator
from src.config import settings


class FFmpegService:
    """FFmpeg service facade for backward compatibility."""
    
    def __init__(self):
        self.ffmpeg_path = settings.get_ffmpeg_bin()
        self.ffprobe_path = settings.get_ffprobe_bin()
        self._encoder = FFEncoder(self.ffmpeg_path, settings.ffmpeg_timeout)
        self._prober = FFProber(self.ffprobe_path)
        self._metrics = MetricsCalculator(self.ffmpeg_path, settings.ffmpeg_timeout)

    async def get_video_info(self, video_path):
        return await self._prober.get_video_info(video_path)

    async def run_command(self, cmd):
        import asyncio
        proc = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        _, stderr = await proc.communicate()
        if proc.returncode != 0:
            raise RuntimeError(stderr.decode())


ffmpeg_service = FFmpegService()

__all__ = ["FFmpegService", "ffmpeg_service"]
