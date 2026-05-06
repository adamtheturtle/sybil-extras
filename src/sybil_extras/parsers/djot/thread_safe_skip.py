"""A thread-safe custom directive skip parser for Djot."""

import re
from collections.abc import Iterable

from beartype import beartype
from sybil import Document, Region
from sybil.parsers.abstract import AbstractSkipParser

from sybil_extras.evaluators.thread_safe_skip import ThreadSafeSkipper
from sybil_extras.parsers.djot.lexers import DirectiveInDjotCommentLexer


@beartype
class ThreadSafeSkipParser:
    """A thread-safe custom directive skip parser for Djot."""

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
