"""A custom directive skip parser for reST."""

from sybil.parsers.abstract import AbstractSkipParser
from sybil.parsers.rest.lexers import DirectiveInCommentLexer


class CustomDirectiveSkipParser(AbstractSkipParser):
    """A custom directive skip parser for reST."""

    def __init__(self, directive: str) -> None:
        """
        Args:
            directive: The name of the directive to skip.
        """
        super().__init__([DirectiveInCommentLexer(directive=directive)])
