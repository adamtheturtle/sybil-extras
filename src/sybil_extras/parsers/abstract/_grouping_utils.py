"""
Shared utilities for grouping parsers.
"""

from collections.abc import Sequence

from sybil import Example
from sybil.region import Lexeme


def combine_examples_text(
    examples: Sequence[Example],
    *,
    pad_groups: bool,
) -> Lexeme:
    """Combine text from multiple examples.

    Pad the examples with newlines to ensure that line numbers in
    error messages match the line numbers in the source.

    Args:
        examples: The examples to combine.
        pad_groups: Whether to pad groups with empty lines.
            This is useful for error messages that reference line numbers.
            However, this is detrimental to commands that expect the file
            to not have a bunch of newlines in it, such as formatters.

    Returns:
        The combined text.
    """
    result = examples[0].parsed
    for example in examples[1:]:
        existing_lines = len(result.text.splitlines())
        if pad_groups:
            padding_lines = example.line - examples[0].line - existing_lines
        else:
            padding_lines = 1

        padding = "\n" * padding_lines
        result = Lexeme(
            text=result.text + padding + example.parsed,
            offset=result.offset,
            line_offset=result.line_offset,
        )

    return Lexeme(
        text=result.text,
        offset=result.offset,
        line_offset=result.line_offset,
    )
