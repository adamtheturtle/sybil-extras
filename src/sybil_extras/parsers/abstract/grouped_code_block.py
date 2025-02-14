"""
A group parser for reST.
"""

from collections.abc import Iterable, Sequence

from sybil import Document, Region
from sybil.parsers.abstract.lexers import LexerCollection
from sybil.region import Lexeme
from sybil.typing import Lexer


def _validate_sub_regions(regions: Sequence[Region]) -> None:
    """
    Raise an error if sub-regions do not all have the same evaluator.
    """
    evaluators = {region.evaluator for region in regions}
    if len(evaluators) != 1:
        message = "All sub-regions of a group must have the same evaluator."
        raise ValueError(message)


class AbstractGroupedCodeBlockParser:
    """
    An abstract parser for grouping code blocks.
    """

    def __init__(self, lexers: Sequence[Lexer]) -> None:
        """
        Args:
            lexers: The lexers to use to find regions.
        """
        self.lexers: LexerCollection = LexerCollection(lexers)

    def __call__(self, document: Document) -> Iterable[Region]:
        """
        Yield regions to evaluate, grouped by start and end comments.
        """
        lexed_regions = self.lexers(document)
        start_end_pairs = zip(lexed_regions, lexed_regions, strict=True)
        current_sub_regions: Sequence[Region] = []
        for start_region, end_region in start_end_pairs:
            current_sub_regions = []
            for _, region in document.regions:
                if start_region.start < region.start < end_region.end:
                    current_sub_regions = [*current_sub_regions, region]
                elif region.start > end_region.start:
                    break
            if current_sub_regions:
                _validate_sub_regions(regions=current_sub_regions)
                first_sub_region = current_sub_regions[0]

                parsed_text = "\n".join(
                    region.parsed for region in current_sub_regions
                )

                parsed = Lexeme(
                    text=parsed_text,
                    line_offset=first_sub_region.parsed.line_offset,
                    offset=first_sub_region.parsed.offset,
                )

                for current_sub_region in current_sub_regions:
                    document.regions.remove(
                        (current_sub_region.start, current_sub_region)
                    )

                yield Region(
                    start=first_sub_region.start,
                    end=first_sub_region.end,
                    parsed=parsed,
                    evaluator=first_sub_region.evaluator,
                )
                break
