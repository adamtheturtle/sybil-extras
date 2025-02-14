"""
A group parser for reST.
"""

from sybil.parsers.rest.lexers import DirectiveInCommentLexer

from sybil_extras.parsers.abstract.grouped_code_block import (
    AbstractGroupedCodeBlockParser,
)


class GroupedCodeBlockParser(AbstractGroupedCodeBlockParser):
    """
    A code block group parser for reST.
    """

    def __init__(self, directive: str) -> None:
        """
        Args:
            directive: The name of the directive to use for grouping.
        """
        lexers = [DirectiveInCommentLexer(directive=directive)]
        super().__init__(lexers=lexers)
