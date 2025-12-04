"""
Custom reStructuredText lexers.
"""

from collections.abc import Iterable

from beartype import beartype
from sybil import Document, Region
from sybil.parsers.rest.lexers import DirectiveInCommentLexer


@beartype
class DirectiveInCommentLexerWithTrailingNewline(DirectiveInCommentLexer):
    """
    A lexer that tolerates missing trailing newlines at the end of a document.
    """

    def __call__(self, document: Document) -> Iterable[Region]:
        """
        Yield directive regions, padding text with a newline when necessary.
        """
        original_text = document.text
        original_end = document.end
        needs_newline = not original_text.endswith("\n")
        if needs_newline:
            document.text = f"{original_text}\n"
            document.end = len(document.text)

        try:
            yield from super().__call__(document)
        finally:
            if needs_newline:
                document.text = original_text
                document.end = original_end
