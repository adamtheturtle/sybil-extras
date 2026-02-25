"""An evaluator for running shell commands on pycon code blocks.

This module provides an evaluator that extracts Python code from pycon-style
code blocks (containing lines with ``>>>`` and ``...`` prompts), runs a tool
on the extracted code, and optionally writes back the results in pycon format,
preserving any output lines from the original.
"""

import ast
import contextlib
import subprocess
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import TYPE_CHECKING

from beartype import beartype
from sybil import Example

from sybil_extras.evaluators._subprocess_utils import (
    lstrip_newlines,
    run_command,
)
from sybil_extras.evaluators.code_block_writer import CodeBlockWriterEvaluator
from sybil_extras.evaluators.shell_evaluator import TempFilePathMaker

if TYPE_CHECKING:
    from sybil.typing import Evaluator


@beartype
def _pycon_to_python(pycon_text: str) -> str:
    """Extract Python input lines from pycon content.

    Strip ``>>> `` and ``... `` prefixes from input lines.
    Discard output lines (lines that do not start with a prompt).

    Args:
        pycon_text: The content of a pycon code block, including ``>>>``
            and ``...`` prompt prefixes and any output lines.

    Returns:
        The extracted Python source code with prompts removed.
    """
    lines: list[str] = []
    for line in pycon_text.splitlines(keepends=True):
        stripped = line.rstrip("\n\r")
        if stripped == ">>>":
            lines.append("\n")
        elif line.startswith(">>> "):
            lines.append(line[4:])
        elif stripped == "...":
            lines.append("\n")
        elif line.startswith("... "):
            lines.append(line[4:])
        # Output lines are discarded.
    return "".join(lines)


@beartype
def _parse_pycon_chunks(
    pycon_text: str,
) -> list[tuple[list[str], list[str]]]:
    """Parse pycon content into a list of (input_lines, output_lines)
    chunks.

    Each chunk represents one interactive statement: the input lines (with
    prompts stripped) and the output lines (as-is, no prompt).

    Args:
        pycon_text: The content of a pycon code block.

    Returns:
        A list of ``(input_lines, output_lines)`` tuples.
    """
    chunks: list[tuple[list[str], list[str]]] = []
    current_input: list[str] = []
    current_output: list[str] = []
    have_current = False

    for line in pycon_text.splitlines(keepends=True):
        stripped = line.rstrip("\n\r")
        if stripped == ">>>" or line.startswith(">>> "):
            if have_current:
                chunks.append((current_input, current_output))
                current_input = []
                current_output = []
            have_current = True
            input_line = "\n" if stripped == ">>>" else line[4:]
            current_input.append(input_line)
        elif stripped == "..." or line.startswith("... "):
            if have_current:  # pragma: no branch
                input_line = "\n" if stripped == "..." else line[4:]
                current_input.append(input_line)
        elif have_current:  # pragma: no branch
            current_output.append(line)

    if have_current:  # pragma: no branch
        chunks.append((current_input, current_output))

    return chunks


@beartype
def _python_to_pycon(python_text: str, original_pycon: str) -> str:
    """Convert formatted Python code back to pycon format.

    Adds ``>>> `` to the first line of each top-level statement and ``... ``
    to continuation lines. Output lines from the original pycon content are
    preserved and appended after each corresponding statement.

    If the number of statements in the formatted Python differs from the
    number of chunks in the original pycon, output lines are not preserved.

    Args:
        python_text: Formatted Python source code (no prompts).
        original_pycon: The original pycon content, used to extract output
            lines for preservation.

    Returns:
        The pycon-formatted version of ``python_text``.
    """
    original_chunks = _parse_pycon_chunks(pycon_text=original_pycon)

    try:
        tree = ast.parse(source=python_text)
    except SyntaxError:
        # Fallback: prefix every line with >>>
        return "".join(
            ">>> " + line for line in python_text.splitlines(keepends=True)
        )

    python_lines = python_text.splitlines(keepends=True)
    statements = tree.body
    preserve_output = len(statements) == len(original_chunks)

    result: list[str] = []
    for i, stmt in enumerate(iterable=statements):
        # ast line numbers are 1-indexed and end_lineno is inclusive,
        # so python_lines[lineno-1:end_lineno] gives the statement lines.
        start = stmt.lineno - 1
        end = stmt.end_lineno
        stmt_lines = python_lines[start:end]

        if stmt_lines:  # pragma: no branch
            result.append(">>> " + stmt_lines[0])
            result.extend("... " + line for line in stmt_lines[1:])

        if preserve_output:
            _input_lines, output_lines = original_chunks[i]
            result.extend(output_lines)

    return "".join(result)


@beartype
class PyconsShellCommandEvaluator:
    """Run a shell command on pycon (Python Console) code blocks.

    This evaluator extracts Python source from pycon-style code blocks,
    writes it to a temporary file, runs a shell command on that file, and
    optionally writes the result back to the document in pycon format,
    preserving any output lines from the original block.

    Args:
        args: The shell command to run. The temporary file path is appended
            as the final argument.
        temp_file_path_maker: A callable that generates the temporary file
            path for an example.
        env: Environment variables for the shell command. If ``None``, the
            current process environment is used.
        newline: Newline convention for the temporary file. If ``None``,
            the system default is used.
        pad_file: Whether to pad the temporary file with leading newlines so
            that the code starts at its actual line number in the document.
            Useful for tools that report line numbers.
        write_to_file: Whether to write any changes made by the command back
            to the source document. Useful for formatters.
        use_pty: Whether to run the command inside a pseudo-terminal.
            Enables color output from tools. Not supported on Windows.
        encoding: Encoding for reading and writing files. If ``None``,
            the system default is used.
    """

    def __init__(
        self,
        *,
        args: Sequence[str | Path],
        temp_file_path_maker: TempFilePathMaker,
        env: Mapping[str, str] | None = None,
        newline: str | None = None,
        pad_file: bool,
        write_to_file: bool,
        use_pty: bool,
        encoding: str | None = None,
    ) -> None:
        """Initialize the evaluator."""
        self._args = args
        self._temp_file_path_maker = temp_file_path_maker
        self._env = env
        self._newline = newline
        self._pad_file = pad_file
        self._write_to_file = write_to_file
        self._use_pty = use_pty
        self._encoding = encoding
        self._namespace_key = "_pycon_shell_evaluator_modified_content"

        if write_to_file:
            self._evaluator: Evaluator = CodeBlockWriterEvaluator(
                evaluator=self._run,
                namespace_key=self._namespace_key,
                encoding=encoding,
            )
        else:
            self._evaluator = self._run

    def _run(self, example: Example) -> None:
        """Extract Python from pycon, run the command, and store the
        result.
        """
        if self._use_pty and sys.platform == "win32":  # pragma: no cover
            msg = "Pseudo-terminal not supported on Windows."
            raise ValueError(msg)

        pycon_content = str(object=example.parsed)
        python_content = _pycon_to_python(pycon_text=pycon_content)

        padding_line = (
            example.line + example.parsed.line_offset if self._pad_file else 0
        )
        python_with_padding = "\n" * padding_line + python_content

        # Ensure a trailing newline; many tools expect it.
        if not python_with_padding.endswith("\n"):  # pragma: no cover
            python_with_padding += "\n"

        temp_file = self._temp_file_path_maker(example=example)
        temp_file.write_text(
            data=python_with_padding,
            encoding=self._encoding,
            newline=self._newline,
        )

        temp_file_content = ""
        try:
            result = run_command(
                command=[
                    str(object=item) for item in [*self._args, temp_file]
                ],
                env=self._env,
                use_pty=self._use_pty,
            )
            with contextlib.suppress(FileNotFoundError):
                temp_file_content = temp_file.read_text(
                    encoding=self._encoding,
                )
        finally:
            with contextlib.suppress(FileNotFoundError):
                temp_file.unlink()

        if self._write_to_file:
            formatted_python = lstrip_newlines(
                input_string=temp_file_content,
                number_of_newlines=padding_line,
            )
            new_pycon = _python_to_pycon(
                python_text=formatted_python,
                original_pycon=pycon_content,
            )
            example.document.namespace[self._namespace_key] = new_pycon

        if result.returncode != 0:
            raise subprocess.CalledProcessError(
                cmd=result.args,
                returncode=result.returncode,
                output=result.stdout,
                stderr=result.stderr,
            )

    def __call__(self, example: Example) -> None:
        """Run the shell command on the pycon example."""
        self._evaluator(example)
