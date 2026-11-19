"""Internal utilities for running shell commands and handling output.

These helpers are shared across evaluators within this package and are not
part of the public API.
"""

import contextlib
import errno
import math
import os
import select
import signal
import subprocess
import sys
import time
from collections.abc import Generator, Iterable, Mapping
from io import BytesIO
from pathlib import Path
from typing import IO

from beartype import beartype

from sybil_extras.evaluators import _windows_subprocess

_CHUNK_SIZE = 1024


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
        # Linux reports the end of a pseudo-terminal stream as `EIO`.
        if use_pty and error.errno == errno.EIO:
            return b""
        raise


@beartype
def _wait_for_output(
    *, descriptors: Iterable[int], deadline: float | None
) -> None:
    """Wait for a readable stream or the deadline."""
    remaining = (
        None if deadline is None else max(0.0, deadline - time.monotonic())
    )
    if sys.platform == "win32":  # pragma: no cover
        # Windows select only accepts sockets, so poll the pipes instead.
        time.sleep(0.01 if remaining is None else min(remaining, 0.01))
    else:
        poll = select.poll()
        for fd in descriptors:
            poll.register(fd, select.POLLIN)
        milliseconds = (
            None
            if remaining is None
            else math.ceil(min(remaining, 1.0) * 1000)
        )
        _ = poll.poll(milliseconds)


@beartype
def _stream_output(
    *,
    streams: dict[int, IO[bytes] | BytesIO],
    use_pty: bool,
    command: list[str | Path],
    timeout: float | None,
    deadline: float | None,
) -> None:
    """Forward raw bytes until the streams close or the deadline
    expires.
    """
    if sys.platform != "win32":  # pragma: no branch
        for fd in streams:
            os.set_blocking(fd, False)

    while bool(streams):
        if (
            timeout is not None
            and deadline is not None
            and time.monotonic() >= deadline
        ):
            raise subprocess.TimeoutExpired(cmd=command, timeout=timeout)

        for fd, output in tuple(streams.items()):
            chunk = _read_available(fd=fd, use_pty=use_pty)
            if chunk == b"":
                del streams[fd]
            elif chunk is not None:
                _ = output.write(chunk)
                output.flush()
        if bool(streams):
            _wait_for_output(descriptors=streams, deadline=deadline)


@beartype
def _output_streams(
    *,
    process: subprocess.Popen[bytes],
    pty_master: int | None,
) -> dict[int, IO[bytes] | BytesIO]:
    """Route the pseudo-terminal or pipes to the standard streams."""
    if pty_master is not None:
        return {pty_master: sys.stdout.buffer}
    if process.stdout is None or process.stderr is None:  # pragma: no cover
        msg = "Expected stdout and stderr pipes."
        raise RuntimeError(msg)
    return {
        process.stdout.fileno(): sys.stdout.buffer,
        process.stderr.fileno(): sys.stderr.buffer,
    }


@contextlib.contextmanager
def _command_process(
    *,
    command: list[str | Path],
    env: Mapping[str, str] | None,
    use_pty: bool,
    limited: bool,
) -> Generator[tuple[subprocess.Popen[bytes], int | None]]:
    """Open the command and its streams, then clean up on exit.

    Raises:
        BaseException: Any exception from the command or caller, after cleanup.
    """
    with contextlib.ExitStack() as cleanup:
        output_fd: int = subprocess.PIPE
        master_fd = None
        with contextlib.ExitStack() as close_slave:
            if use_pty and sys.platform != "win32":  # pragma: no branch
                master_fd, slave_fd = os.openpty()
                _ = cleanup.callback(os.close, fd=master_fd)
                _ = close_slave.callback(os.close, fd=slave_fd)
                output_fd = slave_fd

            job = None
            creationflags = 0
            if limited and sys.platform == "win32":  # pragma: no cover
                job = cleanup.enter_context(
                    cm=_windows_subprocess.job_object()
                )
                creationflags = _windows_subprocess.CREATE_SUSPENDED

            # The caller supplies and must trust the executable and arguments.
            # This function runs the command without adding a shell.
            process = cleanup.enter_context(
                cm=subprocess.Popen(  # noqa: S603
                    args=command,
                    stdout=output_fd,
                    stderr=output_fd,
                    stdin=subprocess.DEVNULL,
                    env=env,
                    start_new_session=limited and sys.platform != "win32",
                    creationflags=creationflags,
                )
            )

        try:
            if sys.platform == "win32" and job is not None:  # pragma: no cover
                _windows_subprocess.start_in_job(job=job, pid=process.pid)
            yield process, master_fd
        except BaseException:
            if limited:
                if sys.platform == "win32":  # pragma: no cover
                    try:
                        if job is not None:
                            _windows_subprocess.terminate_job(job=job)
                    finally:
                        # Also handles failure to assign the job.
                        process.kill()
                else:
                    # The group can still exist after the direct child exits.
                    with contextlib.suppress(ProcessLookupError):
                        os.killpg(process.pid, signal.SIGKILL)
                _ = process.wait()
            raise


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
        TimeoutExpired: If the command or its output exceeds
            the deadline.
    """
    deadline = None if timeout is None else time.monotonic() + timeout
    with _command_process(
        command=command, env=env, use_pty=use_pty, limited=timeout is not None
    ) as (process, master_fd):
        _stream_output(
            streams=_output_streams(process=process, pty_master=master_fd),
            use_pty=use_pty,
            command=command,
            timeout=timeout,
            deadline=deadline,
        )
        try:
            return_code = process.wait(
                timeout=None
                if deadline is None
                else max(0.0, deadline - time.monotonic())
            )
        except subprocess.TimeoutExpired:
            if timeout is None:  # pragma: no cover
                raise
            raise subprocess.TimeoutExpired(
                cmd=command, timeout=timeout
            ) from None

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
