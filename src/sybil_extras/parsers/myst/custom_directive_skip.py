"""
A custom directive skip parser for MyST.
"""

from sybil.parsers.abstract import AbstractSkipParser
from sybil.parsers.markdown.lexers import DirectiveInHTMLCommentLexer
from sybil.parsers.myst.lexers import (
    DirectiveInPercentCommentLexer,
)


class CustomDirectiveSkipParser(AbstractSkipParser):
    """
    A custom directive skip parser for MyST.
    """

    def __init__(self, directive: str) -> None:
        """
        Args:
            directive: The name of the directive to skip.
        """
        # This matches the ``sybil.parsers.myst.SkipParser``, other than
        # it does not hardcode the directive "skip".
        super().__init__(
            lexers=[
                DirectiveInPercentCommentLexer(directive=directive),
                DirectiveInHTMLCommentLexer(directive=directive),
            ]
        )
