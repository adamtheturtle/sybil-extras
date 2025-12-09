"""
A custom directive skip parser for Djot.
"""

import re
from collections.abc import Iterable

from beartype import beartype
from sybil import Document, Region
from sybil.evaluators.skip import Skipper
from sybil.parsers.abstract import AbstractSkipParser

from sybil_extras.parsers.djot.lexers import DirectiveInDjotCommentLexer


@beartype
class CustomDirectiveSkipParser:
    """
    A custom directive skip parser for Djot.
    """

    def __init__(self, directive: str) -> None:
        """
        Args:
            directive: The name of the directive to use for skipping.
        """
        lexers = [
            DirectiveInDjotCommentLexer(
                directive=re.escape(pattern=directive),
            ),
        ]
        self._abstract_skip_parser = AbstractSkipParser(lexers=lexers)
        self._abstract_skip_parser.skipper = Skipper(directive=directive)
        self._abstract_skip_parser.directive = directive

    def __call__(self, document: Document) -> Iterable[Region]:
        """
        Yield skip regions.
        """
        return self._abstract_skip_parser(document=document)

    def get_skipper(self) -> Skipper:
        """
        Return the skipper used by the parser.
        """
        return self._abstract_skip_parser.skipper
