"""An evaluator for running shell commands on example files."""

import contextlib
import os
import platform
import subprocess
import sys
import threading
import uuid
from collections.abc import Mapping, Sequence
from io import BytesIO
from pathlib import Path
from typing import IO, TYPE_CHECKING, Protocol, runtime_checkable

from beartype import beartype
from sybil import Example
from sybil.evaluators.python import pad

from sybil_extras.evaluators.code_block_writer import CodeBlockWriterEvaluator

if TYPE_CHECKING:
    from sybil.typing import Evaluator


@beartype
@runtime_checkable
class _ExampleModified(Protocol):
    """A protocol for a callback to run when an example is modified."""

    def __call__(
        self,
        *,
        example: Example,
        modified_example_content: str,
    ) -> None:
        """This function is called when an example is modified."""
        # We disable a pylint warning here because the ellipsis is required
        # for Pyright to recognize this as a protocol.
        ...  # pylint: disable=unnecessary-ellipsis


@beartype
@runtime_checkable
class TempFilenameGenerator(Protocol):
    """A protocol for generating temporary file paths for examples.

    This allows full customization of the temporary file name used when
    running shell commands on documentation examples.
    """

    def __call__(
        self,
        *,
        example: Example,
    ) -> Path:
        """Generate a temporary file path for an example.

        Args:
            example: The Sybil example for which to generate a filename.

        Returns:
            A Path object for the temporary file. The file should typically
            be created in the same directory as the source file
            (``example.path.parent``) so that relative imports and
            tool configurations work correctly.
        """
        # We disable a pylint warning here because the ellipsis is required
        # for Pyright to recognize this as a protocol.
        ...  # pylint: disable=unnecessary-ellipsis


@beartype
def _run_command(
    *,
    command: list[str | Path],
    env: Mapping[str, str] | None = None,
    use_pty: bool,
) -> subprocess.CompletedProcess[bytes]:
    """Run a command in a pseudo-terminal to preserve color."""
    chunk_size = 1024

    @beartype
    def _process_stream(
        stream_fileno: int,
        output: IO[bytes] | BytesIO,
    ) -> None:
        """Write from an input stream to an output stream."""
        while chunk := os.read(stream_fileno, chunk_size):
            output.write(chunk)
            output.flush()

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
                args=(process.stdout.fileno(), sys.stdout.buffer),
            )
            stderr_thread = threading.Thread(
                target=_process_stream,
                args=(process.stderr.fileno(), sys.stderr.buffer),
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
    """Count the number of leading newlines in a string.

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
def _lstrip_newlines(input_string: str, number_of_newlines: int) -> str:
    """Removes a specified number of newlines from the start of the string.

    Args:
        input_string: The input string to process.
        number_of_newlines: The number of newlines to remove from the
            start.

    Returns:
        The string with the specified number of leading newlines removed.
        If fewer newlines exist, removes all of them.
    """
    num_leading_newlines = _count_leading_newlines(s=input_string)
    lines_to_remove = min(num_leading_newlines, number_of_newlines)
    return input_string[lines_to_remove:]


@beartype
def _create_default_temp_file_path(
    *,
    example: Example,
    suffix: str = "",
) -> Path:
    """Create a temporary file path for an example code block.

    This is a test helper function that generates temporary file paths
    with informative names for debugging.

    The temporary file is created in the same directory as the source
    file and includes the source filename and line number in its name
    for easier identification in error messages.

    Args:
        example: The Sybil example for which to generate a filename.
        suffix: The suffix to use for the temporary file, e.g. ``".py"``.

    Returns:
        A Path object for the temporary file.
    """
    path_name = Path(example.path).name
    # Replace characters that are not allowed in file names for Python
    # modules.
    sanitized_path_name = path_name.replace(".", "_").replace("-", "_")
    line_number_specifier = f"l{example.line}"
    prefix = f"{sanitized_path_name}_{line_number_specifier}_"

    # Create a sibling file in the same directory as the example file.
    # The name also looks like the example file name.
    # This is so that output reflects the actual file path.
    # This is useful for error messages, and for ignores.
    parent = Path(example.path).parent
    return parent / f"{prefix}{uuid.uuid4().hex[:4]}{suffix}"


@beartype
class _ShellCommandRunner:
    """
    Run a shell command on an example file (internal
    implementation).
    """

    def __init__(
        self,
        *,
        args: Sequence[str | Path],
        temp_filename_generator: TempFilenameGenerator,
        env: Mapping[str, str] | None = None,
        newline: str | None = None,
        pad_file: bool,
        write_to_file: bool,
        use_pty: bool,
        encoding: str | None = None,
        on_modify: _ExampleModified | None = None,
        namespace_key: str = "",
    ) -> None:
        """Initialize the shell command runner.

        Args:
            args: The shell command to run.
            temp_filename_generator: A callable that generates the temporary
                file path for an example.
            env: The environment variables to use when running the shell
                command.
            newline: The newline string to use for the temporary file.
            pad_file: Whether to pad the file with newlines at the start.
            write_to_file: Whether to write changes to the file.
            use_pty: Whether to use a pseudo-terminal for running commands.
            encoding: The encoding to use for the temporary file.
            on_modify: A callback to run when the example is modified.
            namespace_key: The key to store modified content in the namespace.
        """
        self._args = args
        self._env = env
        self._pad_file = pad_file
        self._temp_filename_generator = temp_filename_generator
        self._write_to_file = write_to_file
        self._newline = newline
        self._use_pty = use_pty
        self._encoding = encoding
        self._on_modify = on_modify
        self._namespace_key = namespace_key

    def __call__(self, example: Example) -> None:
        """Run the shell command on the example file."""
        if (
            self._use_pty and platform.system() == "Windows"
        ):  # pragma: no cover
            msg = "Pseudo-terminal not supported on Windows."
            raise ValueError(msg)

        padding_line = (
            example.line + example.parsed.line_offset if self._pad_file else 0
        )
        source = pad(
            source=example.parsed,
            line=padding_line,
        )
        temp_file = self._temp_filename_generator(example=example)

        # The parsed code block at the end of a file is given without a
        # trailing newline.  Some tools expect that a file has a trailing
        # newline.  This is especially true for formatters.  We add a
        # newline to the end of the file if it is missing.
        new_source = source + "\n" if not source.endswith("\n") else source
        temp_file.write_text(
            data=new_source,
            encoding=self._encoding,
            newline=self._newline,
        )

        temp_file_content = ""
        try:
            result = _run_command(
                command=[
                    str(object=item) for item in [*self._args, temp_file]
                ],
                env=self._env,
                use_pty=self._use_pty,
            )

            with contextlib.suppress(FileNotFoundError):
                temp_file_content = temp_file.read_text(
                    encoding=self._encoding
                )
        finally:
            with contextlib.suppress(FileNotFoundError):
                temp_file.unlink()

        if new_source != temp_file_content and self._on_modify is not None:
            self._on_modify(
                example=example,
                modified_example_content=temp_file_content,
            )

        if self._write_to_file:
            # Examples are given with no leading newline.
            # While it is possible that a formatter added leading newlines,
            # we assume that this is not the case, and we remove any leading
            # newlines from the replacement which were added by the padding.
            new_region_content = _lstrip_newlines(
                input_string=temp_file_content,
                number_of_newlines=padding_line,
            )
            example.document.namespace[self._namespace_key] = (
                new_region_content
            )

        if result.returncode != 0:
            raise subprocess.CalledProcessError(
                cmd=result.args,
                returncode=result.returncode,
                output=result.stdout,
                stderr=result.stderr,
            )


@beartype
class ShellCommandEvaluator:
    """Run a shell command on the example file."""

    def __init__(
        self,
        *,
        args: Sequence[str | Path],
        temp_filename_generator: TempFilenameGenerator,
        env: Mapping[str, str] | None = None,
        newline: str | None = None,
        # For some commands, padding is good: e.g. we want to see the error
        # reported on the correct line for `mypy`. For others, padding is bad:
        # e.g. `ruff format` expects the file to be formatted without a bunch
        # of newlines at the start.
        pad_file: bool,
        write_to_file: bool,
        use_pty: bool,
        encoding: str | None = None,
        on_modify: _ExampleModified | None = None,
    ) -> None:
        """Initialize the evaluator.

        Args:
            args: The shell command to run.
            temp_filename_generator: A callable that generates the temporary
                file path for an example. The callable receives the example
                and should return a Path for the temporary file.
            env: The environment variables to use when running the shell
                command.
            newline: The newline string to use for the temporary file.
                If ``None``, use the system default.
            pad_file: Whether to pad the file with newlines at the start.
                This is useful for error messages that report the line number.
                However, this is detrimental to commands that expect the file
                to not have a bunch of newlines at the start, such as
                formatters.
            write_to_file: Whether to write changes to the file. This is useful
                for formatters.
            use_pty: Whether to use a pseudo-terminal for running commands.
                This can be useful e.g. to get color output, but can also break
                in some environments. Not supported on Windows.
            encoding: The encoding to use reading documents which include a
                given example, and for the temporary file. If ``None``,
                use the system default.
            on_modify: A callback to run when the example is modified by the
                evaluator.

        Raises:
            ValueError: If pseudo-terminal is requested on Windows.
        """
        namespace_key = "_shell_evaluator_modified_content"
        runner = _ShellCommandRunner(
            args=args,
            temp_filename_generator=temp_filename_generator,
            env=env,
            newline=newline,
            pad_file=pad_file,
            write_to_file=write_to_file,
            use_pty=use_pty,
            encoding=encoding,
            on_modify=on_modify,
            namespace_key=namespace_key,
        )

        if write_to_file:
            self._evaluator: Evaluator = CodeBlockWriterEvaluator(
                evaluator=runner,
                namespace_key=namespace_key,
                encoding=encoding,
            )
        else:
            self._evaluator = runner

    def __call__(self, example: Example) -> None:
        """Run the shell command on the example file."""
        self._evaluator(example)
