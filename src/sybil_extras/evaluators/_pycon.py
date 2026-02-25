"""Internal pycon conversion utilities.

This module handles conversion between pycon format (interactive Python
sessions with ``>>>`` and ``...`` prompts) and plain Python source code,
preserving output lines during round-trips.
"""

import ast
from dataclasses import dataclass

from beartype import beartype


@beartype
def pycon_to_python(pycon_text: str) -> str:
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
@dataclass
class _PyconChunk:
    """A parsed pycon interaction chunk."""

    _input_lines: list[str]
    output_lines: list[str]


@beartype
@dataclass
class _PyconTranscript:
    """A parsed pycon transcript."""

    chunks: list[_PyconChunk]

    @classmethod
    def from_text(cls, *, pycon_text: str) -> "_PyconTranscript":
        """Parse pycon content into transcript chunks.

        Each chunk represents one interactive statement: the input lines
        (with prompts stripped) and the output lines (as-is, no prompt).

        Args:
            pycon_text: The content of a pycon code block.

        Returns:
            A parsed transcript.
        """
        chunks: list[_PyconChunk] = []
        current_input: list[str] = []
        current_output: list[str] = []
        have_current = False

        for line in pycon_text.splitlines(keepends=True):
            stripped = line.rstrip("\n\r")
            if stripped == ">>>" or line.startswith(">>> "):
                if have_current:
                    chunks.append(
                        _PyconChunk(
                            _input_lines=current_input,
                            output_lines=current_output,
                        )
                    )
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
            chunks.append(
                _PyconChunk(
                    _input_lines=current_input,
                    output_lines=current_output,
                )
            )

        return cls(chunks=chunks)


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
def _is_separator_group(*, group: list[str]) -> bool:
    """Return True if the group contains only bare prompts (no code)."""
    return all(line.rstrip("\n\r") in {">>>", "..."} for line in group)


@beartype
def _render_pycon_from_python(
    *,
    python_text: str,
    original_transcript: _PyconTranscript,
) -> str:
    """Render Python source back to pycon using an original transcript."""
    original_chunks = original_transcript.chunks

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

    # Check if output can be preserved.  When the group count matches the
    # chunk count directly, use a simple 1:1 mapping.  Otherwise, ignore
    # separator groups (bare ``>>>`` blank lines added by formatters) and
    # check if the *substantive* groups match the original chunks.
    if len(groups) == len(original_chunks):
        # Direct 1:1 match - every group gets its chunk's output.
        chunk_for_group: list[int | None] = list(range(len(groups)))
    else:
        substantive = [
            i
            for i, g in enumerate(iterable=groups)
            if not _is_separator_group(group=g)
        ]
        if len(substantive) == len(original_chunks):
            chunk_for_group = [None] * len(groups)
            for c_idx, group_idx in enumerate(iterable=substantive):
                chunk_for_group[group_idx] = c_idx
        else:
            chunk_for_group = [None] * len(groups)

    result: list[str] = []
    for i, group in enumerate(iterable=groups):
        result.extend(group)
        matched_chunk = chunk_for_group[i]
        if matched_chunk is not None:
            result.extend(original_chunks[matched_chunk].output_lines)

    return "".join(result)


@beartype
def python_to_pycon(python_text: str, original_pycon: str) -> str:
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
    transcript = _PyconTranscript.from_text(pycon_text=original_pycon)
    return _render_pycon_from_python(
        python_text=python_text,
        original_transcript=transcript,
    )
