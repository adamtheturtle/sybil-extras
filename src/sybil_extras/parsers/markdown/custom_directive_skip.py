"""
A custom directive skip parser for Markdown.
"""

from sybil.parsers.abstract import AbstractSkipParser
from sybil.parsers.markdown.lexers import DirectiveInHTMLCommentLexer


class CustomDirectiveSkipParser(AbstractSkipParser):
    """
    A custom directive skip parser for Markdown.
    """

    def __init__(self, directive: str) -> None:
        """
        Args:
            directive: The name of the directive to skip.
        """
        # This matches the ``sybil.parsers.markdown.SkipParser``, other than
        # it does not hardcode the directive "skip".
        super().__init__(
            lexers=[DirectiveInHTMLCommentLexer(directive=directive)],
        )
