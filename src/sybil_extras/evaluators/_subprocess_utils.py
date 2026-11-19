"""Internal utilities for running shell commands and handling output.

These helpers are shared across evaluators within this package and are not
part of the public API.
"""

import contextlib
import errno
import os
import signal
import subprocess
import sys
import threading
import time
from collections.abc import Mapping
from functools import partial
from io import BytesIO
from pathlib import Path
from typing import IO

from beartype import beartype

from sybil_extras.evaluators import _windows_subprocess

_CHUNK_SIZE = 1024


@beartype
def _write_chunk(*, output: IO[bytes] | BytesIO, chunk: bytes) -> None:
    """Forward a chunk immediately, including under test capture."""
    _ = output.write(chunk)
    output.flush()


@beartype
def _process_stream(
    *,
    stream_fileno: int,
    output: IO[bytes] | BytesIO,
) -> None:
    """Write from an input stream to an output stream."""
    while bool(chunk := os.read(stream_fileno, _CHUNK_SIZE)):
        _write_chunk(output=output, chunk=chunk)


@beartype
def _read_available(*, fd: int, use_pty: bool) -> bytes | None:
    """Read one chunk, returning None if there is no data yet."""
    if sys.platform == "win32":  # pragma: no cover
        return _windows_subprocess.read_pipe(fd=fd, size=_CHUNK_SIZE)

    try:
        return os.read(fd, _CHUNK_SIZE)
    except BlockingIOError:
        return None
    except OSError as error:  # pragma: no cover
        # Linux reports end-of-stream on a PTY master as EIO.
        if use_pty and error.errno == errno.EIO:
            return b""
        raise


@beartype
def _stream_until_deadline(
    *,
    process: subprocess.Popen[bytes],
    streams: dict[int, IO[bytes] | BytesIO],
    use_pty: bool,
    deadline: float,
    timeout: float,
) -> int:
    """Drain output and wait for the command within the same deadline."""
    if sys.platform != "win32":  # pragma: no branch
        for fd in streams:
            os.set_blocking(fd, False)

    # A nonblocking read avoids leaving reader threads behind when a
    # descendant inherits an output descriptor and keeps it open.
    while bool(streams):
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise subprocess.TimeoutExpired(cmd=process.args, timeout=timeout)
        made_progress = False
        for fd, output in tuple(streams.items()):
            chunk = _read_available(fd=fd, use_pty=use_pty)
            if chunk is None:
                continue
            made_progress = True
            if bool(chunk):
                _write_chunk(output=output, chunk=chunk)
            else:
                del streams[fd]
        if not made_progress:
            time.sleep(min(remaining, 0.01))

    try:
        return process.wait(timeout=max(0.0, deadline - time.monotonic()))
    except subprocess.TimeoutExpired:
        # Report the caller's timeout, even when output used part of it.
        raise subprocess.TimeoutExpired(
            cmd=process.args, timeout=timeout
        ) from None


@beartype
def _stream_without_deadline(
    *,
    streams: dict[int, IO[bytes] | BytesIO],
    use_pty: bool,
) -> None:
    """Stream output using the original blocking reads."""
    if use_pty:
        with contextlib.suppress(OSError):
            for fd, output in streams.items():
                _process_stream(stream_fileno=fd, output=output)
        return

    # Popen requires real file descriptors. Test frameworks may replace
    # sys.stdout.buffer and sys.stderr.buffer with in-memory capture objects,
    # so forward each pipe's output concurrently instead.
    threads = [
        threading.Thread(
            target=partial(_process_stream, stream_fileno=fd, output=output),
        )
        for fd, output in streams.items()
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()


@beartype
def _output_streams(
    *,
    process: subprocess.Popen[bytes],
    pty_master: int | None,
) -> dict[int, IO[bytes] | BytesIO]:
    """Route PTY output to stdout or forward each pipe separately."""
    if pty_master is not None:
        return {pty_master: sys.stdout.buffer}
    if process.stdout is None or process.stderr is None:  # pragma: no cover
        msg = "Expected stdout and stderr pipes."
        raise RuntimeError(msg)
    return {
        process.stdout.fileno(): sys.stdout.buffer,
        process.stderr.fileno(): sys.stderr.buffer,
    }


@beartype
def run_command(
    *,
    command: list[str | Path],
    env: Mapping[str, str] | None,
    use_pty: bool,
    timeout: float | None,
) -> subprocess.CompletedProcess[bytes]:
    """Run a command, optionally inside a pseudo-terminal to preserve
    color.

    Args:
        command: The command and arguments to execute.
        env: Optional environment variable mapping. If None, the current
            process environment is inherited.
        use_pty: Run inside a pseudo-terminal. Not supported on Windows.
        timeout: Maximum time in seconds to run the command and drain
            its output, or None for unlimited execution.

    Returns:
        A CompletedProcess object. stdout and stderr are None because
        output is streamed directly.

    Raises:
        subprocess.TimeoutExpired: If the command or its output exceeds
            the deadline.
    """
    with contextlib.ExitStack() as cleanup:
        stdout: int = subprocess.PIPE
        stderr: int = subprocess.PIPE
        master_fd = None
        with contextlib.ExitStack() as close_slave:
            if use_pty and sys.platform != "win32":  # pragma: no branch
                master_fd, slave_fd = os.openpty()
                _ = cleanup.callback(os.close, fd=master_fd)
                _ = close_slave.callback(os.close, fd=slave_fd)
                stdout = stderr = slave_fd

            job = None
            creationflags = 0
            if (
                timeout is not None and sys.platform == "win32"
            ):  # pragma: no cover
                job = cleanup.enter_context(cm=_windows_subprocess.Job())
                creationflags = job.creationflags

            deadline = (
                time.monotonic() + timeout if timeout is not None else 0.0
            )
            # The caller supplies and must trust the executable and arguments.
            # This function runs the command without adding a shell.
            process = cleanup.enter_context(
                cm=subprocess.Popen(  # noqa: S603
                    args=command,
                    stdout=stdout,
                    stderr=stderr,
                    stdin=subprocess.DEVNULL,
                    env=env,
                    start_new_session=timeout is not None
                    and sys.platform != "win32",
                    creationflags=creationflags,
                )
            )

        try:
            streams = _output_streams(process=process, pty_master=master_fd)
            if timeout is None:
                _stream_without_deadline(streams=streams, use_pty=use_pty)
                return_code = process.wait()
            else:
                if job is not None:  # pragma: no cover
                    job.start(process=process)
                return_code = _stream_until_deadline(
                    process=process,
                    streams=streams,
                    use_pty=use_pty,
                    deadline=deadline,
                    timeout=timeout,
                )
        except BaseException:
            if timeout is not None:
                if sys.platform == "win32":  # pragma: no cover
                    try:
                        if job is not None:
                            job.terminate()
                    finally:
                        # Also handles failure to assign the job.
                        process.kill()
                else:
                    # The group can still exist after the direct child exits.
                    with contextlib.suppress(ProcessLookupError):
                        os.killpg(process.pid, signal.SIGKILL)
                _ = process.wait()
            raise

    return subprocess.CompletedProcess(
        args=command,
        returncode=return_code,
        stdout=None,
        stderr=None,
    )


@beartype
def _count_leading_newlines(s: str) -> int:
    """Count the number of leading newline characters in a string.

    Args:
        s: The input string.

    Returns:
        The number of leading newlines.
    """
    count = 0
    non_newline_found = False
    for char in s:
        if char == "\n" and not non_newline_found:
            count += 1
        else:
            non_newline_found = True
    return count


@beartype
def lstrip_newlines(*, input_string: str, number_of_newlines: int) -> str:
    """Remove a specified number of leading newlines from a string.

    Args:
        input_string: The input string to process.
        number_of_newlines: The number of leading newlines to remove.
            If the string has fewer leading newlines, all are removed.

    Returns:
        The string with at most ``number_of_newlines`` leading newlines
        removed.
    """
    num_leading = _count_leading_newlines(s=input_string)
    lines_to_remove = min(num_leading, number_of_newlines)
    return input_string[lines_to_remove:]
