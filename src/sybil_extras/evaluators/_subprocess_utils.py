"""Internal utilities for running shell commands and handling output.

These helpers are shared across evaluators within this package and are not
part of the public API.
"""

import contextlib
import os
import subprocess
import sys
from collections.abc import Mapping
from pathlib import Path

from beartype import beartype

STDOUT_FILENO = 1


@beartype
def _forward_stream_to_fd(
    *,
    stream_fileno: int,
    output_fileno: int,
) -> None:
    """Write from an input stream to an output file descriptor."""
    chunk_size = 1024
    while chunk := os.read(stream_fileno, chunk_size):  # pragma: no branch
        os.write(output_fileno, chunk)


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
                # Click capture redirects file descriptor 1, while
                # ``sys.stdout.fileno()`` points at the saved original.
                _forward_stream_to_fd(
                    stream_fileno=stdout_master_fd,
                    output_fileno=STDOUT_FILENO,
                )

            os.close(fd=stdout_master_fd)
            return_code = process.wait()

    else:
        with subprocess.Popen(
            args=command,
            stdin=subprocess.PIPE,
            env=env,
        ) as process:
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
