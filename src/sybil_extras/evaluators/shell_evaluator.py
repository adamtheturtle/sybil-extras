"""Setup for Sybil."""

import shlex
import subprocess
import tempfile
import textwrap
from collections.abc import Mapping, Sequence
from pathlib import Path

from beartype import beartype
from sybil import Example
from sybil.evaluators.python import pad


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
        tempfile_suffix: str = "",
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
            tempfile_suffix: The suffix to use for the temporary file.
                This is useful for commands that expect a specific file suffix.
                For example `pre-commit` hooks which expect `.py` files.
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
        self._tempfile_suffix = tempfile_suffix
        self._pad_file = pad_file
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

        prefix = (
            Path(example.path).name.replace(".", "_") + f"_l{example.line}_"
        )
        with tempfile.NamedTemporaryFile(
            # Create a sibling file in the same directory as the example file.
            # The name also looks like the example file name.
            # This is so that output reflects the actual file path.
            # This is useful for error messages, and for ignores.
            prefix=prefix,
            dir=Path(example.path).parent,
            mode="w+",
            delete=True,
            suffix=".example" + self._tempfile_suffix,
        ) as f:
            # The parsed code block at the end of a file is given without a
            # trailing newline.  Some tools expect that a file has a trailing
            # newline.  This is especially true for formatters.  We add a
            # newline to the end of the file if it is missing.
            new_source = source + "\n" if not source.endswith("\n") else source
            f.write(new_source)
            f.flush()
            temp_file_path = Path(f.name)

            result = subprocess.run(
                args=[*self._args, temp_file_path],
                capture_output=True,
                check=False,
                text=True,
                env=self._env,
            )

            temp_file_content = temp_file_path.read_text(encoding="utf-8")

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

            modified_content = existing_file_content.replace(
                # Some regions are given to us with a trailing newline, and
                # some are not.  We need to remove the trailing newline from
                # the existing region content to avoid a double newline.
                #
                # There is no such thing as a code block with two trailing
                # newlines, so we need not worry about tools which add this.
                indented_existing_region_content.rstrip("\n"),
                indented_temp_file_content.rstrip("\n"),
                1,
            )

            existing_file_path.write_text(
                data=modified_content,
                encoding="utf-8",
            )

        if result.returncode != 0:
            joined_command = shlex.join(
                split_command=[str(item) for item in self._args],
            )
            msg = (
                f"Shell command failed:\n"
                f"Command: {joined_command}\n"
                f"Output: {result.stdout}\n"
                f"Error: {result.stderr}"
            )

            raise ValueError(msg)
