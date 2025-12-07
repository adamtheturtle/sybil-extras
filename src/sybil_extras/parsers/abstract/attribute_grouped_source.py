"""An attribute-based group parser.

This parser groups code blocks based on attribute values in fenced code
blocks.
"""

from collections import defaultdict
from collections.abc import Iterable

from beartype import beartype
from sybil import Document, Example, Region
from sybil.typing import Evaluator, Parser

from ._grouping_utils import create_combined_region


@beartype
def _first_example_start_offset(examples: list[Example]) -> int:
    """
    Get the character offset where this group first appears.
    """
    return examples[0].region.start


@beartype
class AbstractAttributeGroupedSourceParser:
    """An abstract parser for grouping code blocks by attribute values.

    This parser groups code blocks that have the same value for a
    specified attribute.
    """

    def __init__(
        self,
        *,
        code_block_parser: Parser,
        evaluator: Evaluator,
        attribute_name: str,
        pad_groups: bool,
        ungrouped_evaluator: Evaluator,
    ) -> None:
        """
        Args:
            code_block_parser: A code block parser instance that parses
                attributes.
            evaluator: The evaluator to use for evaluating the combined region.
            attribute_name: The attribute name to use for grouping.
            pad_groups: Whether to pad groups with empty lines.
                This is useful for error messages that reference line numbers.
                However, this is detrimental to commands that expect the file
                to not have a bunch of newlines in it, such as formatters.
            ungrouped_evaluator: The evaluator to use for code blocks that
                don't have the grouping attribute.
        """
        self._code_block_parser = code_block_parser
        self._evaluator = evaluator
        self._attribute_name = attribute_name
        self._pad_groups = pad_groups
        self._ungrouped_evaluator = ungrouped_evaluator

    def __call__(self, document: Document) -> Iterable[Region]:
        """Parse the document and yield grouped regions.

        This works in two phases:
        1. Collect all code blocks and group them by attribute
        2. Yield combined regions for each group in document order
        """
        examples_by_group: dict[str, list[Example]] = defaultdict(list)
        ungrouped_regions: list[Region] = []

        for region in self._code_block_parser(document):
            attributes = region.lexemes.get("attributes", {})
            group_name: str | None = attributes.get(self._attribute_name)
            if not group_name:
                ungrouped_regions.append(
                    Region(
                        start=region.start,
                        end=region.end,
                        parsed=region.parsed,
                        evaluator=self._ungrouped_evaluator,
                        lexemes=region.lexemes,
                    )
                )
                continue

            # Create an example from the region to collect metadata.
            # We need line numbers for padding calculation in
            # _combine_examples_text.
            #
            # Region only provides character offsets (start/end), but Example
            # requires line/column numbers. We calculate these the same way
            # Sybil does internally in Document.line_column().
            source = region.lexemes["source"]
            line = document.text.count("\n", 0, region.start) + 1
            column = region.start - document.text.rfind("\n", 0, region.start)
            example = Example(
                document=document,
                line=line,
                column=column,
                region=region,
                namespace={},
            )
            # Set the example's parsed to the source lexeme
            example.parsed = source

            examples_by_group[group_name].append(example)

        sorted_groups = sorted(
            examples_by_group.values(),
            key=_first_example_start_offset,
        )

        for examples in sorted_groups:
            combined_region = create_combined_region(
                examples=examples,
                evaluator=self._evaluator,
                pad_groups=self._pad_groups,
            )

            # We use examples[0].region.end instead of examples[-1].region.end
            # to avoid region overlap errors when groups are interleaved in
            # the document.
            #
            # Sybil explicitly forbids overlapping regions to avoid ambiguity
            # in which example "owns" a particular section of the document.
            #
            # This means that the region we yield has the wrong end position.
            yield Region(
                start=combined_region.start,
                end=examples[0].region.end,
                parsed=combined_region.parsed,
                evaluator=combined_region.evaluator,
                lexemes=combined_region.lexemes,
            )

        # Yield ungrouped regions
        yield from ungrouped_regions
