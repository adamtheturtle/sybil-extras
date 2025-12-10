"""
Lexers for norg.
"""

import re
from collections.abc import Iterable

from beartype import beartype
from sybil import Document, Region


@beartype
class DirectiveInNorgCommentLexer:
    """A lexer for directives in norg infirm tags (single-line macros).

    Norg infirm tags use the syntax: .tag-name parameter1 parameter2
    For directives, we expect: .directive: argument

    This lexer extracts the following lexemes:
    - ``directive`` as a str
    - ``arguments`` as a str

    Args:
        directive: A str containing a regular expression pattern to match
            directive names.
        arguments: A str containing a regular expression pattern to match
            directive arguments.
        mapping: If provided, this is used to rename lexemes from the keys in
            the mapping to their values. Only mapped lexemes will be returned
            in any Region objects.
    """

    def __init__(
        self,
        directive: str,
        arguments: str = r".*?",
        mapping: dict[str, str] | None = None,
    ) -> None:
        """
        Initialize the norg infirm tag lexer.
        """
        # Pattern to match norg infirm tags with directives
        # Format: .directive: argument or .directive
        # The tag must be at the beginning of a line (with optional leading
        # whitespace)
        pattern = (
            rf"^\s*\.(?P<directive>{directive})"
            rf"(?:\s*:\s*(?P<arguments>{arguments}))?$"
        )
        self.pattern: re.Pattern[str] = re.compile(
            pattern=pattern, flags=re.MULTILINE
        )
        self.mapping = mapping

    def __call__(self, document: Document) -> Iterable[Region]:
        """
        Yield regions for norg infirm tag directives.
        """
        for match in self.pattern.finditer(string=document.text):
            lexemes = match.groupdict()
            # Clean up the arguments - might be None if no colon was present
            if lexemes["arguments"] is not None:
                lexemes["arguments"] = lexemes["arguments"].strip()
            else:
                lexemes["arguments"] = ""

            if self.mapping:
                lexemes = {
                    dest: lexemes[source]
                    for source, dest in self.mapping.items()
                }

            yield Region(
                start=match.start(),
                end=match.end(),
                lexemes=lexemes,
            )
