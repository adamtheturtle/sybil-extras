"""A thread-safe custom directive skip parser for MDX."""

import re
from collections.abc import Iterable

from beartype import beartype
from sybil import Document, Region
from sybil.parsers.abstract import AbstractSkipParser
from sybil.parsers.markdown.lexers import DirectiveInHTMLCommentLexer

from sybil_extras.evaluators.thread_safe_skip import ThreadSafeSkipper
from sybil_extras.parsers.mdx.lexers import DirectiveInJSXCommentLexer


@beartype
class ThreadSafeSkipParser:
    """A thread-safe custom directive skip parser for MDX."""

    def __init__(self, directive: str) -> None:
        """
        Args:
            directive: The directive name to match inside HTML or JSX
                comments.
        """
        escaped_directive = re.escape(pattern=directive)
        lexers = [
            DirectiveInHTMLCommentLexer(directive=escaped_directive),
            DirectiveInJSXCommentLexer(directive=escaped_directive),
        ]
        self._abstract_skip_parser = AbstractSkipParser(lexers=lexers)
        self._skipper = ThreadSafeSkipper(directive=directive)
        self._abstract_skip_parser.skipper = self._skipper
        self._abstract_skip_parser.directive = directive

    def __call__(self, document: Document) -> Iterable[Region]:
        """Yield skip regions and register the thread-safe skipper."""
        regions = list(self._abstract_skip_parser(document=document))
        if regions:
            document.push_evaluator(evaluator=self._skipper)
        return regions

    def get_skipper(self) -> ThreadSafeSkipper:
        """Return the thread-safe skipper used by the parser."""
        return self._skipper
