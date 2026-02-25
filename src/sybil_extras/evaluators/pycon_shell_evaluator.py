"""An evaluator for running shell commands on pycon code blocks.

This module provides an evaluator that extracts Python code from pycon-style
code blocks (containing lines with ``>>>`` and ``...`` prompts), runs a tool
on the extracted code, and optionally writes back the results in pycon format,
preserving any output lines from the original.
"""

import ast
from collections.abc import Mapping, Sequence
from pathlib import Path

from beartype import beartype
from sybil import Example

from sybil_extras.evaluators.shell_evaluator import (
    TempFilePathMaker,
    create_evaluator,
)


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
            if have_current:
                input_line = "\n" if stripped == "..." else line[4:]
                current_input.append(input_line)
        elif have_current:
            current_output.append(line)

    if have_current:
        chunks.append((current_input, current_output))

    return chunks


@beartype
def _with_pycon_prompt(*, prompt: str, line: str) -> str:
    """Prefix a line with a pycon prompt, preserving bare prompts."""
    if line in {"", "\n", "\r\n"}:
        return prompt + line
    return f"{prompt} {line}"


@beartype
def _continuation_line_indices(*, tree: ast.Module) -> set[int]:
    """Return zero-based indices of continuation lines in multi-line
    statements.
    """
    continuation_lines: set[int] = set()
    for stmt in tree.body:
        start = stmt.lineno - 1
        end = stmt.end_lineno or stmt.lineno
        for line_idx in range(start + 1, end):
            continuation_lines.add(line_idx)
    return continuation_lines


@beartype
def _python_lines_to_pycon_groups(
    *,
    python_lines: list[str],
    continuation_lines: set[int],
) -> list[list[str]]:
    """Build pycon prompt groups from Python lines."""
    groups: list[list[str]] = []
    for i, line in enumerate(iterable=python_lines):
        if i in continuation_lines:
            groups[-1].append(_with_pycon_prompt(prompt="...", line=line))
        elif (
            groups
            and line.strip("\r\n") == ""
            and groups[-1][-1].startswith("... ")
        ):
            # Preserve the trailing bare ``...`` prompt used to terminate a
            # block in interactive sessions.
            groups[-1].append(_with_pycon_prompt(prompt="...", line=line))
        else:
            groups.append([_with_pycon_prompt(prompt=">>>", line=line)])
    return groups


@beartype
def _python_to_pycon(python_text: str, original_pycon: str) -> str:
    """Convert formatted Python code back to pycon format.

    Adds ``>>> `` to the first line of each top-level statement and ``... ``
    to continuation lines.  Lines not belonging to any AST statement (such
    as comments or blank lines) also receive ``>>> ``.  Output lines from
    the original pycon content are preserved when the number of ``>>>``
    groups matches the number of original pycon chunks.

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

    # Build groups: each group is a ``>>>`` line followed by zero or more
    # ``...`` continuation lines.
    continuation_lines = _continuation_line_indices(tree=tree)
    groups = _python_lines_to_pycon_groups(
        python_lines=python_lines,
        continuation_lines=continuation_lines,
    )

    preserve_output = len(groups) == len(original_chunks)

    result: list[str] = []
    for i, group in enumerate(iterable=groups):
        result.extend(group)
        if preserve_output:
            _input_lines, output_lines = original_chunks[i]
            result.extend(output_lines)

    return "".join(result)


@beartype
class _PyconSourcePreparer:
    """Extract Python source from pycon content."""

    def __call__(self, *, example: Example) -> str:
        """Return the Python code extracted from the pycon example."""
        return _pycon_to_python(pycon_text=str(object=example.parsed))


@beartype
class _PyconResultTransformer:
    """Convert formatted Python back to pycon format."""

    def __call__(self, *, content: str, example: Example) -> str:
        """Return the pycon-formatted version of the formatted Python."""
        return _python_to_pycon(
            python_text=content,
            original_pycon=str(object=example.parsed),
        )


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
        self._evaluator = create_evaluator(
            args=args,
            temp_file_path_maker=temp_file_path_maker,
            env=env,
            newline=newline,
            pad_file=pad_file,
            write_to_file=write_to_file,
            use_pty=use_pty,
            encoding=encoding,
            namespace_key="_pycon_shell_evaluator_modified_content",
            source_preparer=_PyconSourcePreparer(),
            result_transformer=_PyconResultTransformer(),
        )

    def __call__(self, example: Example) -> None:
        """Run the shell command on the pycon example."""
        self._evaluator(example)
