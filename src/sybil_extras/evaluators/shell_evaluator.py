"""
An evaluator for running shell commands on example files.
"""

import contextlib
import os
import platform
import subprocess
import sys
import textwrap
import threading
import uuid
from collections.abc import Mapping, Sequence
from io import BytesIO
from pathlib import Path
from typing import IO, Protocol, runtime_checkable

from beartype import beartype
from sybil import Example
from sybil.evaluators.python import pad


@beartype
@runtime_checkable
class _ExampleModified(Protocol):
    """
    A protocol for a callback to run when an example is modified.
    """

    def __call__(
        self,
        *,
        example: Example,
        modified_example_content: str,
    ) -> None:
        """
        This function is called when an example is modified.
        """
        # We disable a pylint warning here because the ellipsis is required
        # for Pyright to recognize this as a protocol.
        ...  # pylint: disable=unnecessary-ellipsis


@beartype
def _get_modified_region_text(
    example: Example,
    original_region_text: str,
    new_code_block_content: str,
) -> str:
    """
    Get the region text to use after the example content is replaced.
    """
    first_line = original_region_text.split(sep="\n")[0]
    code_block_indent_prefix = first_line[
        : len(first_line) - len(first_line.lstrip())
    ]

    if example.parsed:
        within_code_block_indent_prefix = (
            _get_within_code_block_indentation_prefix(example=example)
        )
        replace_old_not_indented = example.parsed
        replace_new_prefix = ""
    # This is a break of the abstraction, - we really should not have
    # to know about markup language specifics here.
    elif original_region_text.endswith("```"):
        # Markdown or MyST
        within_code_block_indent_prefix = code_block_indent_prefix
        replace_old_not_indented = "\n"
        replace_new_prefix = "\n"
    else:
        # reStructuredText
        within_code_block_indent_prefix = code_block_indent_prefix + "   "
        replace_old_not_indented = "\n"
        replace_new_prefix = "\n\n"

    indented_example_parsed = textwrap.indent(
        text=replace_old_not_indented,
        prefix=within_code_block_indent_prefix,
    )
    replacement_text = textwrap.indent(
        text=new_code_block_content,
        prefix=within_code_block_indent_prefix,
    )

    if not replacement_text.endswith("\n"):
        replacement_text += "\n"

    text_to_replace_index = original_region_text.rfind(indented_example_parsed)
    text_before_replacement = original_region_text[:text_to_replace_index]
    text_after_replacement = original_region_text[
        text_to_replace_index + len(indented_example_parsed) :
    ]
    region_with_replaced_text = (
        text_before_replacement
        + replace_new_prefix
        + replacement_text
        + text_after_replacement
    )
    stripped_of_newlines_region = region_with_replaced_text.rstrip("\n")
    # Keep the same number of newlines at the end of the region.
    num_newlines_at_end = len(original_region_text) - len(
        original_region_text.rstrip("\n")
    )
    newlines_at_end = "\n" * num_newlines_at_end
    return stripped_of_newlines_region + newlines_at_end


@beartype
def _run_command(
    *,
    command: list[str | Path],
    env: Mapping[str, str] | None = None,
    use_pty: bool,
) -> subprocess.CompletedProcess[bytes]:
    """
    Run a command in a pseudo-terminal to preserve color.
    """
    chunk_size = 1024

    @beartype
    def _process_stream(
        stream_fileno: int,
        output: IO[bytes] | BytesIO,
    ) -> None:
        """
        Write from an input stream to an output stream.
        """
        while chunk := os.read(stream_fileno, chunk_size):
            output.write(chunk)
            output.flush()

    if use_pty:
        stdout_master_fd = -1
        slave_fd = -1
        with contextlib.suppress(AttributeError):
            stdout_master_fd, slave_fd = os.openpty()

        stdout = slave_fd
        stderr = slave_fd
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
def _get_within_code_block_indentation_prefix(example: Example) -> str:
    """
    Get the indentation of the parsed code in the example.
    """
    first_line = str(object=example.parsed).split(sep="\n", maxsplit=1)[0]
    region_text = example.document.text[
        example.region.start : example.region.end
    ]
    region_lines = region_text.splitlines()
    region_lines_matching_first_line = [
        line for line in region_lines if line.lstrip() == first_line.lstrip()
    ]
    first_region_line_matching_first_line = region_lines_matching_first_line[0]

    left_padding_region_line = len(
        first_region_line_matching_first_line
    ) - len(first_region_line_matching_first_line.lstrip())
    left_padding_parsed_line = len(first_line) - len(first_line.lstrip())
    indentation_length = left_padding_region_line - left_padding_parsed_line
    indentation_character = first_region_line_matching_first_line[0]
    return indentation_character * indentation_length


@beartype
class ShellCommandEvaluator:
    """
    Run a shell command on the example file.
    """

    def __init__(
        self,
        *,
        args: Sequence[str | Path],
        env: Mapping[str, str] | None = None,
        tempfile_suffixes: Sequence[str] = (),
        tempfile_name_prefix: str = "",
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
            env: The environment variables to use when running the shell
                command.
            tempfile_suffixes: The suffixes to use for the temporary file.
                This is useful for commands that expect a specific file suffix.
                For example `pre-commit` hooks which expect `.py` files.
            tempfile_name_prefix: The prefix to use for the temporary file.
                This is useful for distinguishing files created by a user of
                this evaluator from other files, e.g. for ignoring in linter
                configurations.
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
        self._args = args
        self._env = env
        self._pad_file = pad_file
        self._tempfile_name_prefix = tempfile_name_prefix
        self._tempfile_suffixes = tempfile_suffixes
        self._write_to_file = write_to_file
        self._newline = newline
        self._use_pty = use_pty
        self._encoding = encoding
        self._on_modify = on_modify

    def __call__(self, example: Example) -> None:
        """
        Run the shell command on the example file.
        """
        if (
            self._use_pty and platform.system() == "Windows"
        ):  # pragma: no cover
            msg = "Pseudo-terminal not supported on Windows."
            raise ValueError(msg)

        if self._pad_file:
            source = pad(
                source=example.parsed,
                line=example.line + example.parsed.line_offset,
            )
        else:
            source = example.parsed

        path_name = Path(example.path).name
        # Replace characters that are not allowed in file names for Python
        # modules.
        sanitized_path_name = path_name.replace(".", "_").replace("-", "_")
        line_number_specifier = f"l{example.line}"
        prefix = f"{sanitized_path_name}_{line_number_specifier}_"

        if self._tempfile_name_prefix:
            prefix = f"{self._tempfile_name_prefix}_{prefix}"

        suffix = "".join(self._tempfile_suffixes)

        # Create a sibling file in the same directory as the example file.
        # The name also looks like the example file name.
        # This is so that output reflects the actual file path.
        # This is useful for error messages, and for ignores.
        parent = Path(example.path).parent
        temp_file = parent / f"{prefix}_{uuid.uuid4().hex[:4]}_{suffix}"
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

        new_region_content = temp_file_content

        if new_source != new_region_content and self._on_modify is not None:
            self._on_modify(
                example=example,
                modified_example_content=new_region_content,
            )

        # Examples are given with no leading newline.
        # While it is possible that a formatter added leading newlines,
        # we assume that this is not the case, and we remove any leading
        # newlines from the replacement which were added by the padding.
        if self._pad_file:
            new_region_content = _lstrip_newlines(
                input_string=new_region_content,
                number_of_newlines=example.line + example.parsed.line_offset,
            )

        original_region_text = example.document.text[
            example.region.start : example.region.end
        ]
        modified_region_text = _get_modified_region_text(
            original_region_text=original_region_text,
            example=example,
            new_code_block_content=new_region_content,
        )

        existing_file_content = example.document.text

        if modified_region_text != original_region_text:
            modified_document_content = (
                existing_file_content[: example.region.start]
                + modified_region_text
                + existing_file_content[example.region.end :]
            )
            if self._write_to_file:
                example.document.text = modified_document_content
                Path(example.path).write_text(
                    data=modified_document_content,
                    encoding=self._encoding,
                )

        if result.returncode != 0:
            raise subprocess.CalledProcessError(
                cmd=result.args,
                returncode=result.returncode,
                output=result.stdout,
                stderr=result.stderr,
            )
