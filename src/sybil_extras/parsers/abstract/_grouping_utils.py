"""
Shared utilities for grouping parsers.
"""

from collections.abc import Sequence

from beartype import beartype
from sybil import Example, Region
from sybil.region import Lexeme
from sybil.typing import Evaluator

from sybil_extras.grouping_markers import (
    BlockPosition,
    GroupDelimiters,
    insert_markers,
)


@beartype
def _combine_examples_text(
    examples: Sequence[Example],
    *,
    pad_groups: bool,
    delimiters: GroupDelimiters | None = None,
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
        delimiters: Optional delimiters to insert between blocks.
            If provided, magic comment markers will be added to mark
            block boundaries.

    Returns:
        The combined text.
    """
    result = examples[0].parsed
    block_positions: list[BlockPosition] = []
    current_line = 0

    # Track the first block
    first_block_lines = len(examples[0].parsed.splitlines())
    block_positions.append(
        BlockPosition(
            start_line=0,
            end_line=first_block_lines,
            block_index=0,
        )
    )
    current_line = first_block_lines

    for block_index, example in enumerate(examples[1:], start=1):
        existing_lines = len(result.text.splitlines())
        if pad_groups:
            padding_lines = example.line - examples[0].line - existing_lines
        else:
            padding_lines = 1

        padding = "\n" * padding_lines
        current_line += padding_lines

        block_start_line = current_line
        example_lines = len(example.parsed.splitlines())
        block_end_line = current_line + example_lines

        block_positions.append(
            BlockPosition(
                start_line=block_start_line,
                end_line=block_end_line,
                block_index=block_index,
            )
        )

        result = Lexeme(
            text=result.text + padding + example.parsed,
            offset=result.offset,
            line_offset=result.line_offset,
        )
        current_line = block_end_line

    combined_text = result.text

    # Insert markers if delimiters are provided
    if delimiters is not None:
        combined_text = insert_markers(
            grouped_source=combined_text,
            block_positions=block_positions,
            delimiters=delimiters,
        )

    return Lexeme(
        text=combined_text,
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


@beartype
def create_combined_region(
    examples: Sequence[Example],
    *,
    evaluator: Evaluator,
    pad_groups: bool,
    delimiters: GroupDelimiters | None = None,
) -> Region:
    """Create a combined region from multiple examples.

    Args:
        examples: The examples to combine.
        evaluator: The evaluator to use for the combined region.
        pad_groups: Whether to pad groups with empty lines.
        delimiters: Optional delimiters to insert between blocks.

    Returns:
        The combined region.
    """
    return Region(
        start=examples[0].region.start,
        end=examples[-1].region.end,
        parsed=_combine_examples_text(
            examples=examples,
            pad_groups=pad_groups,
            delimiters=delimiters,
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
