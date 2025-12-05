"""An attribute-based group parser for MDX.

This parser groups code blocks based on the 'group' attribute in MDX
fenced code blocks, following Docusaurus conventions.
"""

from collections import defaultdict
from collections.abc import Callable, Iterable

from beartype import beartype
from sybil import Document, Region
from sybil.region import Lexeme
from sybil.typing import Evaluator


@beartype
def _combine_source_text(
    *,
    regions: list[Region],
    document: Document,
    pad_groups: bool,
) -> Lexeme:
    """Combine source text from multiple regions.

    Pad the regions with newlines to ensure that line numbers in
    error messages match the line numbers in the source.

    Args:
        regions: The regions to combine (must have 'source' lexeme).
            Must be non-empty.
        document: The document containing the regions.
        pad_groups: Whether to pad groups with empty lines.
            This is useful for error messages that reference line numbers.
            However, this is detrimental to commands that expect the file
            to not have a bunch of newlines in it, such as formatters.

    Returns:
        The combined source text as a Lexeme.
    """
    # Get the source text from the first region
    first_region = regions[0]
    first_source = first_region.lexemes["source"]
    result_text = first_source.text
    result_offset = first_source.offset
    result_line_offset = first_source.line_offset

    # Track line numbers for padding calculation
    first_line = document.text[: first_region.start].count("\n") + 1

    for region in regions[1:]:
        source = region.lexemes["source"]
        current_text = source.text

        if pad_groups:
            current_line = document.text[: region.start].count("\n") + 1
            existing_lines = len(result_text.splitlines())
            padding_lines = current_line - first_line - existing_lines
        else:
            padding_lines = 1

        padding = "\n" * padding_lines
        result_text = result_text + padding + current_text

    return Lexeme(
        text=result_text,
        offset=result_offset,
        line_offset=result_line_offset,
    )


@beartype
class AttributeGroupedSourceParser:
    """A parser for grouping MDX code blocks by attribute values.

    This parser groups code blocks that have the same value for a
    specified attribute (default: 'group').
    """

    def __init__(
        self,
        *,
        code_block_parser: Callable[[Document], Iterable[Region]],
        evaluator: Evaluator,
        attribute_name: str,
        pad_groups: bool,
    ) -> None:
        """
        Args:
            code_block_parser: An MDX CodeBlockParser instance that parses
                attributes.
            evaluator: The evaluator to use for evaluating the combined region.
            attribute_name: The attribute name to use for grouping
                (default: "group").
            pad_groups: Whether to pad groups with empty lines.
                This is useful for error messages that reference line numbers.
                However, this is detrimental to commands that expect the file
                to not have a bunch of newlines in it, such as formatters.
        """
        self._code_block_parser = code_block_parser
        self._evaluator = evaluator
        self._attribute_name = attribute_name
        self._pad_groups = pad_groups

    def __call__(self, document: Document) -> Iterable[Region]:
        """Parse the document and yield grouped regions.

        This works in two phases:
        1. Collect all code blocks and group them by attribute
        2. Yield combined regions for each group in document order
        """
        # First, collect all code blocks and group them by attribute
        regions_by_group: dict[str, list[Region]] = defaultdict(list)

        for region in self._code_block_parser(document):
            attributes = region.lexemes.get("attributes", {})
            group_name: str | None = attributes.get(self._attribute_name)
            if not group_name:
                continue

            regions_by_group[group_name].append(region)

        # Now yield combined regions for each group in document order
        # Sort groups by the start position of their first region
        sorted_groups = sorted(
            regions_by_group.items(),
            key=lambda item: item[1][0].start,
        )

        for _group_name, regions in sorted_groups:
            # Combine the source code from the regions
            combined_source = _combine_source_text(
                regions=regions,
                document=document,
                pad_groups=self._pad_groups,
            )

            # Create a new region that doesn't overlap with others
            # Use only the first region's position for start/end
            # This ensures each group gets its own non-overlapping region
            yield Region(
                start=regions[0].start,
                end=regions[0].end,
                parsed=combined_source,
                evaluator=self._evaluator,
                lexemes=regions[0].lexemes,
            )
