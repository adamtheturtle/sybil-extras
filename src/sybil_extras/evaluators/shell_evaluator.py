"""An evaluator for running shell commands on example files."""

import subprocess
import textwrap
import uuid
from collections.abc import Mapping, Sequence
from pathlib import Path

import tee_subprocess
from beartype import beartype
from sybil import Example
from sybil.evaluators.python import pad


def _count_leading_newlines(s: str) -> int:
    """
    Count the number of leading newlines in a string.

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
    """
    Removes a specified number of newlines from the start of the string.

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
def _get_indentation(example: Example) -> str:
    """Get the indentation of the parsed code in the example."""
    first_line = str(example.parsed).split("\n", 1)[0]
    region_text = example.document.text[
        example.region.start : example.region.end
    ]
    indentations: list[str] = []
    region_lines = region_text.splitlines()
    for region_line in region_lines:
        if region_line.lstrip() == first_line.lstrip():
            left_padding_region_line = len(region_line) - len(
                region_line.lstrip()
            )
            left_padding_parsed_line = len(first_line) - len(
                first_line.lstrip()
            )
            indentation_length = (
                left_padding_region_line - left_padding_parsed_line
            )
            indentation_character = region_line[0]
            indentation = indentation_character * indentation_length
            indentations.append(indentation)

    return indentations[0]


@beartype
class ShellCommandEvaluator:
    """Run a shell command on the example file."""

    def __init__(
        self,
        args: Sequence[str | Path],
        env: Mapping[str, str] | None = None,
        tempfile_suffixes: Sequence[str] = (),
        tempfile_name_prefix: str = "",
        *,
        # For some commands, padding is good: e.g. we want to see the error
        # reported on the correct line for `mypy`. For others, padding is bad:
        # e.g. `ruff format` expects the file to be formatted without a bunch
        # of newlines at the start.
        pad_file: bool,
        write_to_file: bool,
    ) -> None:
        """
        Initialize the evaluator.

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
            pad_file: Whether to pad the file with newlines at the start.
                This is useful for error messages that report the line number.
                However, this is detrimental to commands that expect the file
                to not have a bunch of newlines at the start, such as
                formatters.
            write_to_file: Whether to write changes to the file. This is useful
                for formatters.
        """
        self._args = args
        self._env = env
        self._pad_file = pad_file
        self._tempfile_name_prefix = tempfile_name_prefix
        self._tempfile_suffixes = tempfile_suffixes
        self._write_to_file = write_to_file

    def __call__(self, example: Example) -> None:
        """Run the shell command on the example file."""
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
        temp_file.write_text(new_source, encoding="utf-8")

        args = [*self._args, temp_file]
        args_strings = [str(arg) for arg in args]
        result = tee_subprocess.run(
            args=args_strings,
            check=False,
            capture_output=False,
            text=False,
            env=self._env,
        )

        temp_file_content = temp_file.read_text(encoding="utf-8")
        temp_file.unlink()

        if self._write_to_file:
            existing_file_path = Path(example.path)
            existing_file_content = existing_file_path.read_text(
                encoding="utf-8"
            )
            existing_region_content = example.region.parsed
            indent_prefix = _get_indentation(example=example)
            indented_existing_region_content = textwrap.indent(
                text=existing_region_content,
                prefix=indent_prefix,
            )

            indented_temp_file_content = textwrap.indent(
                text=temp_file_content,
                prefix=indent_prefix,
            )

            # Some regions are given to us with a trailing newline, and
            # some are not.  We need to remove the trailing newline from
            # the existing region content to avoid a double newline.
            #
            # There is no such thing as a code block with two trailing
            # newlines, so we need not worry about tools which add this.
            content_to_replace = indented_existing_region_content.rstrip("\n")
            replacement = indented_temp_file_content.rstrip("\n")

            # Examples are given with no leading newline.
            # While it is possible that a formatter added leading newlines,
            # we assume that this is not the case, and we remove any leading
            # newlines from the replacement which were added by the padding.
            if self._pad_file:
                replacement = _lstrip_newlines(
                    input_string=replacement,
                    number_of_newlines=example.line
                    + example.parsed.line_offset,
                )

            modified_content = existing_file_content.replace(
                content_to_replace,
                replacement,
                1,
            )

            if existing_file_content != modified_content:
                # We avoid writing to the file if the content is the same.
                # This is because writing to the file will update the file's
                # modification time, which can cause unnecessary rebuilds, and
                # we have seen that confuse the Git index.
                existing_file_path.write_text(
                    data=modified_content,
                    encoding="utf-8",
                )

        assert isinstance(result, subprocess.CompletedProcess)
        if result.returncode != 0:
            raise subprocess.CalledProcessError(
                cmd=result.args,
                returncode=result.returncode,
                output=result.stdout,
                stderr=result.stderr,
            )
