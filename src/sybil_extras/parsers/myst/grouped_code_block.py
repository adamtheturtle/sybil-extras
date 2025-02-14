"""
A group parser for MyST.
"""

from sybil.parsers.markdown.lexers import DirectiveInHTMLCommentLexer
from sybil.parsers.myst.lexers import (
    DirectiveInPercentCommentLexer,
)

from sybil_extras.parsers.abstract.grouped_code_block import (
    AbstractGroupedCodeBlockParser,
)


class GroupedCodeBlockParser(AbstractGroupedCodeBlockParser):
    """
    A code block group parser for MyST.
    """

    def __init__(self, directive: str) -> None:
        """
        Args:
            directive: The name of the directive to use for grouping.
        """
        lexers = [
            DirectiveInPercentCommentLexer(directive=directive),
            DirectiveInHTMLCommentLexer(directive=directive),
        ]
        super().__init__(lexers=lexers)
