"""Internal utilities for running shell commands and handling output.

These helpers are shared across evaluators within this package and are not
part of the public API.
"""

import contextlib
import os
import subprocess
import sys
import threading
from collections.abc import Mapping
from io import BytesIO
from pathlib import Path
from typing import IO

from beartype import beartype


@beartype
def _process_stream(
    *,
    stream_fileno: int,
    output: IO[bytes] | BytesIO,
) -> None:
    """Write from an input stream to an output stream."""
    chunk_size = 1024
    while chunk := os.read(stream_fileno, chunk_size):
        output.write(chunk)
        output.flush()


@beartype
def run_command(
    *,
    command: list[str | Path],
    env: Mapping[str, str] | None = None,
    use_pty: bool,
) -> subprocess.CompletedProcess[bytes]:
    """Run a command, optionally inside a pseudo-terminal to preserve
    color.

    Args:
        command: The command and arguments to execute.
        env: Optional environment variable mapping.  If ``None``, the
            current process environment is inherited.
        use_pty: When ``True`` the command is run inside a pseudo-terminal
            so that tools that emit ANSI color codes do so correctly.
            Not supported on Windows.

    Returns:
        A ``CompletedProcess`` object.  ``stdout`` and ``stderr`` are
        ``None`` because output is streamed directly to the parent
        process's file descriptors.
    """
    if use_pty:
        stdout_master_fd: int = -1
        slave_fd: int = -1
        # We use ``hasattr`` rather than
        # ``contextlib.suppress(AttributeError)`` so that ``mypy`` can narrow
        # the type on Windows, where ``os.openpty`` does not exist.
        # We also check ``sys.platform`` so that pyright can narrow the type.
        if sys.platform != "win32" and hasattr(
            os, "openpty"
        ):  # pragma: no branch
            stdout_master_fd, slave_fd = os.openpty()

        stdout: int = slave_fd
        stderr: int = slave_fd
        with subprocess.Popen(
            args=command,
            stdout=stdout,
            stderr=stderr,
            stdin=subprocess.PIPE,
            env=env,
            close_fds=True,
        ) as process:
            os.close(fd=slave_fd)

            # On some platforms, an ``OSError`` is raised when reading from
            # a master file descriptor that has no corresponding slave file.
            # I think that this may be described in
            # https://bugs.python.org/issue5380#msg82827
            with contextlib.suppress(OSError):
                _process_stream(
                    stream_fileno=stdout_master_fd,
                    output=sys.stdout.buffer,
                )

            os.close(fd=stdout_master_fd)

    else:
        # We use ``subprocess.PIPE`` + threads rather than passing
        # ``stdout=sys.stdout.buffer`` directly to ``Popen``.
        #
        # ``Popen`` accepts a file-like object for ``stdout``/``stderr``
        # only if it exposes a real OS file descriptor via ``fileno()``.
        # When test frameworks such as pytest replace ``sys.stdout`` with
        # a ``StringIO``-based capture object, ``sys.stdout.buffer.fileno()``
        # raises ``io.UnsupportedOperation``.
        #
        # By routing data through ``subprocess.PIPE`` we always get genuine
        # OS-level pipe file descriptors.  The background threads then read
        # from those descriptors and write into ``sys.stdout.buffer`` /
        # ``sys.stderr.buffer``, which may be the real terminal or a
        # test-framework capture object — either way the write is safe.
        # This preserves live streaming: output is forwarded chunk-by-chunk
        # rather than being buffered until the process exits.
        with subprocess.Popen(
            args=command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            stdin=subprocess.PIPE,
            env=env,
        ) as process:
            if (
                process.stdout is None or process.stderr is None
            ):  # pragma: no cover
                raise ValueError

            stdout_thread = threading.Thread(
                target=_process_stream,
                kwargs={
                    "stream_fileno": process.stdout.fileno(),
                    "output": sys.stdout.buffer,
                },
            )
            stderr_thread = threading.Thread(
                target=_process_stream,
                kwargs={
                    "stream_fileno": process.stderr.fileno(),
                    "output": sys.stderr.buffer,
                },
            )

            stdout_thread.start()
            stderr_thread.start()

            stdout_thread.join()
            stderr_thread.join()

    return_code = process.wait()

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
