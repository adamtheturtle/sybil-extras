"""
A group parser for reST.
"""

from collections.abc import Iterable, Sequence

from sybil import Document, Region
from sybil.parsers.abstract.lexers import LexerCollection
from sybil.parsers.rest.lexers import DirectiveInCommentLexer
from sybil.region import Lexeme


class GroupParser:
    """
    A group parser for reST.
    """

    def __init__(self, directive: str) -> None:
        """
        Args:
            directive: The name of the directive to use for grouping.
        """
        self.lexers: LexerCollection = LexerCollection(
            [DirectiveInCommentLexer(directive=directive)]
        )

    def __call__(self, document: Document) -> Iterable[Region]:
        """
        Yield regions to evaluate, grouped by start and end comments.
        """
        lexed_regions = self.lexers(document)
        start_end_pairs = [
            (first, second)
            for first, second in zip(lexed_regions, lexed_regions, strict=True)
        ]
        for start_region, end_region in start_end_pairs:
            current_sub_regions: Sequence[Region] = []
            for _, region in document.regions:
                if start_region.start < region.start < end_region.end:
                    current_sub_regions = [*current_sub_regions, region]
                elif region.start > end_region.start:
                    first_sub_region = current_sub_regions[0]
                    last_sub_region = current_sub_regions[-1]

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
                        end=last_sub_region.end,
                        parsed=parsed,
                        evaluator=first_sub_region.evaluator,
                    )
                    break
