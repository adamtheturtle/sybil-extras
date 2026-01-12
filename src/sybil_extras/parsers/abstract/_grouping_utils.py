"""
Shared utilities for grouping parsers.
"""

from collections.abc import Iterable, Sequence

from beartype import beartype
from sybil import Example, Region
from sybil.region import Lexeme
from sybil.typing import Evaluator


@beartype
def count_expected_code_blocks(examples: Iterable[Example]) -> int:
    """Count the expected number of code blocks, accounting for skip markers.

    Skip directives (like 'skip: next' or 'skip: start/end') only affect
    examples that come AFTER them, so we must process in position order.

    Skip markers have parsed values like ('next', None) or ('start', None).

    Only examples with a 'source' lexeme are counted, as these are the only
    examples that will be collected by the GroupAllParser.

    Args:
        examples: The examples to count.

    Returns:
        The number of code blocks expected to be collected.
    """
    examples_sorted = sorted(examples, key=lambda ex: ex.region.start)

    skipped_count = 0
    skip_next = False
    in_skip_range = False
    non_skip_count = 0

    for ex in examples_sorted:
        parsed: object = ex.parsed
        # Skip markers have parsed values like ('next', None)
        if (
            isinstance(parsed, tuple)
            and parsed
            and parsed[0] in {"next", "start", "end"}
        ):
            if parsed[0] == "next":
                skip_next = True
            elif parsed[0] == "start":
                in_skip_range = True
            else:
                in_skip_range = False
        elif has_source(example=ex):
            non_skip_count += 1
            if skip_next or in_skip_range:
                skipped_count += 1
                skip_next = False

    return non_skip_count - skipped_count


def _get_text(parsed: Lexeme | str) -> str:
    """Get text from a parsed value, which may be a Lexeme or a string.

    Args:
        parsed: The parsed value from an example.

    Returns:
        The text content.
    """
    if isinstance(parsed, Lexeme):
        return parsed.text
    return parsed


@beartype
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
    first_parsed = examples[0].parsed
    if isinstance(first_parsed, Lexeme):
        result_text = first_parsed.text
        result_offset = first_parsed.offset
        result_line_offset = first_parsed.line_offset
    else:
        result_text = str(object=first_parsed)
        result_offset = examples[0].region.start
        result_line_offset = 0

    for example in examples[1:]:
        existing_lines = len(result_text.splitlines())
        if pad_groups:
            padding_lines = example.line - examples[0].line - existing_lines
        else:
            padding_lines = 1

        padding = "\n" * padding_lines
        result_text = result_text + padding + _get_text(parsed=example.parsed)

    return Lexeme(
        text=result_text,
        offset=result_offset,
        line_offset=result_line_offset,
    )


@beartype
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


@beartype
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
