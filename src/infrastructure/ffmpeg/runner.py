"""FFmpeg subprocess runner."""
from __future__ import annotations

import asyncio
from typing import Any, Callable, Optional, Sequence, Tuple

StdoutStderr = Tuple[bytes, bytes]
OnSuccess = Callable[[], Any]
AddCommandCallback = Optional[Callable[[str, str, Optional[str]], Any]]
UpdateStatusCallback = Optional[Callable[[Any, str, Optional[str]], Any]]


async def run_ffmpeg_command(
    cmd: Sequence[str],
    *,
    timeout: int,
    add_command_callback: AddCommandCallback = None,
    update_status_callback: UpdateStatusCallback = None,
    command_type: str,
    source_file: Optional[str],
    on_success: OnSuccess,
    error_prefix: str,
    timeout_message: Optional[str] = None,
) -> Any:
    """
    Run an FFmpeg-related command with uniform status tracking and error handling.

    Args:
        cmd: Complete command arguments.
        timeout: Timeout in seconds.
        add_command_callback: Optional callback to record the command.
        update_status_callback: Optional callback to update status.
        command_type: Logical command type (e.g., "psnr", "encode").
        source_file: Originating file for logging.
        on_success: Callable executed after a successful run.
        error_prefix: Error message prefix for exceptions.
        timeout_message: Override default timeout message.

    Returns:
        The result of on_success().

    Raises:
        RuntimeError: When the command fails or times out.
    """
    cmd_id: Any = None
    if add_command_callback:
        cmd_id = add_command_callback(command_type, " ".join(cmd), source_file)
    if update_status_callback and cmd_id is not None:
        update_status_callback(cmd_id, "running")

    try:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout)

        if process.returncode != 0:
            if update_status_callback and cmd_id is not None:
                update_status_callback(cmd_id, "failed", stderr.decode())
            raise RuntimeError(f"{error_prefix}: {stderr.decode()}")

        result = on_success()
        if update_status_callback and cmd_id is not None:
            update_status_callback(cmd_id, "completed")
        return result

    except asyncio.TimeoutError:
        process.kill()
        timeout_msg = timeout_message or f"{error_prefix} timed out"
        if update_status_callback and cmd_id is not None:
            update_status_callback(cmd_id, "failed", timeout_msg)
        raise RuntimeError(timeout_msg)
    except Exception as exc:
        if update_status_callback and cmd_id is not None:
            update_status_callback(cmd_id, "failed", str(exc))
        raise RuntimeError(f"{error_prefix}: {exc}") from exc
