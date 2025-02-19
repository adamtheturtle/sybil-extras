"""
A custom directive skip parser for Markdown.
"""

import re
from collections.abc import Iterable

from sybil import Document, Region
from sybil.evaluators.skip import Skipper
from sybil.parsers.abstract import AbstractSkipParser
from sybil.parsers.markdown.lexers import DirectiveInHTMLCommentLexer


class CustomDirectiveSkipParser:
    """
    A custom directive skip parser for Markdown.
    """

    def __init__(self, directive: str) -> None:
        """
        Args:
            directive: The name of the directive to use for skipping.
        """
        # This matches the ``sybil.parsers.markdown.SkipParser``, other than
        # it does not hardcode the directive "skip".
        lexers = [
            DirectiveInHTMLCommentLexer(directive=re.escape(pattern=directive))
        ]
        self._abstract_skip_parser = AbstractSkipParser(lexers=lexers)
        self._abstract_skip_parser.skipper = Skipper(directive=directive)
        self._abstract_skip_parser.directive = directive

    def __call__(self, document: Document) -> Iterable[Region]:
        """
        Yield skip regions.
        """
        return self._abstract_skip_parser(document=document)

    @property
    def skipper(self) -> Skipper:
        """
        The skipper used by the parser.
        """
        return self._abstract_skip_parser.skipper
