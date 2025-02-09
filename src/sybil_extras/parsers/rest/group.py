"""
A group parser for reST.
"""

from collections.abc import Iterable

from sybil import Document, Region
from sybil.parsers.abstract.lexers import LexerCollection
from sybil.parsers.abstract.skip import SKIP_ARGUMENTS_PATTERN
from sybil.parsers.rest.lexers import DirectiveInCommentLexer


class GroupParser:
    """
    A group parser for reST.
    """

    def __init__(self, directive: str) -> None:
        """
        Args:
            directive: The name of the directive to use for grouping.
        """
        self.lexers = LexerCollection(
            [DirectiveInCommentLexer(directive=directive)]
        )

    def __call__(self, document: Document) -> Iterable[Region]:
        """
        Yield regions to evaluate, grouped by start and end comments.
        """
        for lexed in self.lexers(document):
            arguments = lexed.lexemes["arguments"]
            match = SKIP_ARGUMENTS_PATTERN.match(arguments)
            if match is None:
                directive = lexed.lexemes.get("directive", "group")
                message = f"malformed arguments to {directive}: {arguments!r}"
                raise ValueError(message)
            yield Region(
                start=lexed.start,
                end=lexed.end,
                parsed=match.groups(),
                evaluator=None,
            )
