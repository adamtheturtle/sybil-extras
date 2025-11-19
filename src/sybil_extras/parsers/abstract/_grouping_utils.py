"""
Shared utilities for grouping parsers.
"""

from collections.abc import Sequence

from sybil import Example, Region
from sybil.region import Lexeme
from sybil.typing import Evaluator


def _combine_examples_text(
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


def has_source(example: Example) -> bool:
    """Check if an example has a source lexeme.

    Args:
        example: The example to check.

    Returns:
        True if the example has a source lexeme.
    """
    return "source" in example.region.lexemes


def create_combined_region(
    examples: Sequence[Example],
    *,
    evaluator: Evaluator,
    pad_groups: bool,
) -> Region:
    """Create a combined region from multiple examples.

    Args:
        examples: The examples to combine.
        evaluator: The evaluator to use for the combined region.
        pad_groups: Whether to pad groups with empty lines.

    Returns:
        The combined region.
    """
    return Region(
        start=examples[0].region.start,
        end=examples[-1].region.end,
        parsed=_combine_examples_text(
            examples=examples,
            pad_groups=pad_groups,
        ),
        evaluator=evaluator,
        lexemes=examples[0].region.lexemes,
    )


def create_combined_example(
    examples: Sequence[Example],
    region: Region,
) -> Example:
    """Create a combined example from multiple examples.

    Args:
        examples: The examples that were combined.
        region: The combined region.

    Returns:
        The combined example.
    """
    return Example(
        document=examples[0].document,
        line=examples[0].line,
        column=examples[0].column,
        region=region,
        namespace=examples[0].namespace,
    )
