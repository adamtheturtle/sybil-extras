"""
A custom directive skip parser for reST.
"""

from sybil.parsers.abstract import AbstractSkipParser
from sybil.parsers.rest.lexers import DirectiveInCommentLexer


class CustomDirectiveSkipParser(AbstractSkipParser):
    """
    A custom directive skip parser for reST.
    """

    def __init__(self, directive: str) -> None:
        """
        Args:
            directive: The name of the directive to skip.
        """
        # This matches the ``sybil.parsers.rest.SkipParser``, other than
        # it does not hardcode the directive "skip".
        super().__init__(lexers=[DirectiveInCommentLexer(directive=directive)])
