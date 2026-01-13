"""Lexers for Markdown using the MarkdownIt library.

These lexers use a proper Markdown parsing library instead of regex.
"""

import re
from collections.abc import Iterable

from beartype import beartype
from markdown_it import MarkdownIt
from sybil import Document, Lexeme, Region

from sybil_extras.parsers.markdown_it._line_offsets import line_offsets


@beartype
class DirectiveInHTMLCommentLexer:
    """A lexer for directives embedded in HTML comments using MarkdownIt.

    This lexer finds HTML comments that contain directives in the format:
    ``<!--- directive: arguments -->`` or ``<!-- directive: arguments -->``.

    It yields Region objects with the following lexemes:

    - ``directive`` as a :class:`str`.
    - ``arguments`` as a :class:`str`.
    - ``source`` as a :class:`~sybil.Lexeme` (empty for single-line
      directives, or the content for multi-line directive blocks).

    Args:
        directive: A string containing a regular expression pattern to
            match directive names.
        arguments: A string containing a regular expression pattern to
            match directive arguments.
    """

    def __init__(
        self,
        directive: str,
        arguments: str = ".*?",
    ) -> None:
        """
        Initialize the lexer.
        """
        # Build a pattern to match the directive inside the HTML comment
        # The pattern matches:
        # - Optional leading whitespace (for indented comments)
        # - Optional semicolon and whitespace at the start
        # - The directive name
        # - Optional colon
        # - Optional whitespace
        # - The arguments
        self._directive_pattern = re.compile(
            pattern=rf"^[ \t]*<!--+\s*(?:;\s*)?(?P<directive>{directive})"
            rf":?\s*(?P<arguments>{arguments})\s*"
            rf"(?:--+>|$)",
            flags=re.MULTILINE,
        )

    def __call__(self, document: Document) -> Iterable[Region]:
        """
        Parse the document and yield regions for directive comments.
        """
        md = MarkdownIt()
        # Disable the indented code block rule. Without this, content
        # indented by 4+ spaces would be parsed as a code_block token
        # instead of being recognized as html_block. With the rule
        # disabled, MarkdownIt treats indented HTML comments as html_block
        # tokens, allowing us to find directives in indented sections.
        md.disable(names="code")
        tokens = md.parse(src=document.text)
        offsets = line_offsets(text=document.text)

        for token in tokens:
            if token.type != "html_block":
                continue

            # MarkdownIt always provides map for html_block tokens.
            assert token.map is not None  # noqa: S101

            start_line, end_line = token.map

            # Calculate character positions
            region_start = offsets[start_line]
            if end_line < len(offsets):
                region_end = offsets[end_line]
            else:
                region_end = len(document.text)

            # Try to match our directive pattern against the HTML content
            content = token.content
            match = self._directive_pattern.match(string=content)
            if match is None:
                continue

            directive_name = match.group("directive")
            arguments = match.group("arguments")

            # For simple single-line directives, source is empty
            # For multi-line directive blocks, we would extract the source
            # But for skip/group directives, they are single-line
            source = Lexeme(
                text="",
                offset=0,
                line_offset=0,
            )

            lexemes = {
                "directive": directive_name,
                "arguments": arguments,
                "source": source,
            }

            yield Region(start=region_start, end=region_end, lexemes=lexemes)
