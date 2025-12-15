"""
A custom directive skip parser for MDX.
"""

import re
from collections.abc import Iterable

from beartype import beartype
from sybil import Document, Region
from sybil.evaluators.skip import Skipper
from sybil.parsers.abstract import AbstractSkipParser
from sybil.parsers.markdown.lexers import DirectiveInHTMLCommentLexer

from sybil_extras.parsers.mdx.lexers import DirectiveInJSXCommentLexer


@beartype
class CustomDirectiveSkipParser:
    """
    A custom directive skip parser for MDX using HTML or JSX-style comments.
    """

    def __init__(self, directive: str) -> None:
        """
        Args:
            directive: The directive name to match inside HTML or JSX comments.
        """
        escaped_directive = re.escape(pattern=directive)
        lexers = [
            DirectiveInHTMLCommentLexer(directive=escaped_directive),
            DirectiveInJSXCommentLexer(directive=escaped_directive),
        ]
        self._abstract_skip_parser = AbstractSkipParser(lexers=lexers)
        self._abstract_skip_parser.skipper = Skipper(directive=directive)
        self._abstract_skip_parser.directive = directive

    def __call__(self, document: Document) -> Iterable[Region]:
        """
        Yield skip regions for the given document.
        """
        return self._abstract_skip_parser(document=document)

    def get_skipper(self) -> Skipper:
        """
        Return the skipper handling skip state for this parser.
        """
        return self._abstract_skip_parser.skipper
