"""
Code block parsing for Norg.
"""

import re
from collections.abc import Iterable, Sequence

from beartype import beartype
from sybil import Document, Region
from sybil.parsers.abstract import AbstractCodeBlockParser
from sybil.parsers.markdown.lexers import DirectiveInHTMLCommentLexer
from sybil.region import Lexeme
from sybil.typing import Evaluator, Lexer


class NorgVerbatimRangedTagLexer:
    """A lexer for Norg verbatim ranged tags.

    Norg verbatim ranged tags use the syntax:
    @code
    content here
    @end

    The language can be specified as a parameter:
    @code python
    print("hello")
    @end
    """

    def __init__(
        self,
        language: str,
        mapping: dict[str, str] | None = None,
    ) -> None:
        """Initialize the lexer.

        Args:
            language: A regex pattern matching the language (e.g., "python").
            mapping: Optional mapping to rename lexemes.
        """
        # Pattern to match opening tag: @code or @code python
        # Must be at start of line (with optional leading whitespace)
        # Use [^\S\n]+ instead of \s+ to avoid matching newlines
        self._opening_pattern = re.compile(
            pattern=rf"^\s*@code(?:[^\S\n]+(?P<language>{language}))?$",
            flags=re.MULTILINE,
        )
        # Pattern to match closing tag: @end
        # Must be at start of line (with optional leading whitespace)
        # Allow trailing whitespace after @end for consistency with opening
        self._closing_pattern = re.compile(
            pattern=r"^\s*@end[^\S\n]*$",
            flags=re.MULTILINE,
        )
        self._mapping = mapping

    def __call__(self, document: Document) -> Iterable[Region]:
        """
        Yield regions for Norg verbatim ranged tags.
        """
        index = 0
        while True:
            opening = self._opening_pattern.search(
                string=document.text, pos=index
            )
            if opening is None:
                break

            # Find the matching @end tag
            closing = self._closing_pattern.search(
                string=document.text, pos=opening.end()
            )
            if closing is None:
                # No closing tag found, skip this opening tag
                index = opening.end()
                continue

            # Extract the content between tags.
            # Skip the newline after the opening tag. Since the opening
            # pattern ends with $ (matching before newline) and we found a
            # closing tag after opening.end(), there is always a newline at
            # opening.end().
            content_start = opening.end() + 1

            content_end = closing.start()
            source_text = document.text[content_start:content_end]

            # Build lexemes
            lexemes = opening.groupdict()
            if lexemes.get("language") is None:
                lexemes["language"] = ""
            else:
                lexemes["language"] = lexemes["language"].strip()

            # Calculate the offset from the start of the region to the
            # content
            offset = content_start - opening.start()
            lexemes["source"] = Lexeme(
                text=source_text,
                offset=offset,
                line_offset=0,
            )

            if self._mapping:
                lexemes = {
                    dest: lexemes[source]
                    for source, dest in self._mapping.items()
                }

            yield Region(
                start=opening.start(),
                end=closing.end(),
                lexemes=lexemes,
            )

            index = closing.end()


@beartype
class CodeBlockParser:
    """
    A parser for Norg verbatim ranged tags (code blocks).
    """

    def __init__(
        self,
        *,
        language: str | None = None,
        evaluator: Evaluator | None = None,
    ) -> None:
        """
        Args:
            language: The language to match (for example ``python``).
            evaluator: The evaluator used for the parsed code block.
        """
        lexers: Sequence[Lexer] = [
            NorgVerbatimRangedTagLexer(
                language=r".+",
                mapping={"language": "arguments", "source": "source"},
            ),
            DirectiveInHTMLCommentLexer(
                directive=r"(invisible-)?code(-block)?",
                arguments=".+",
            ),
        ]
        self._parser = AbstractCodeBlockParser(
            lexers=lexers,
            language=language,
            evaluator=evaluator,
        )

    def __call__(self, document: Document) -> Iterable[Region]:
        """
        Yield regions for Norg code blocks.
        """
        return self._parser(document)
