"""Lexers for reStructuredText using the docutils library.

These lexers use a proper RST parsing library instead of regex.
"""

import re
from collections.abc import Iterable

from beartype import beartype
from docutils import nodes
from docutils.frontend import get_default_settings
from docutils.parsers.rst import Parser
from docutils.utils import new_document
from sybil import Document, Lexeme, Region

from sybil_extras.parsers.docutils_rst._line_offsets import line_offsets


@beartype
class DirectiveInCommentLexer:
    """A lexer for directives embedded in RST comments using docutils.

    This lexer finds RST comments that contain directives in the format:
    ``.. directive: arguments`` or ``.. directive arguments``.

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
        # Build a pattern to match the directive inside the comment.
        # RST comments have their content after ".. " with possible
        # indentation.
        # The pattern matches:
        # - Optional leading whitespace
        # - The directive name
        # - Optional colon
        # - Optional whitespace
        # - The arguments
        self._directive_pattern = re.compile(
            pattern=rf"^\s*(?P<directive>{directive}):?\s*(?P<arguments>{arguments})\s*$",
            flags=re.MULTILINE,
        )

    def __call__(self, document: Document) -> Iterable[Region]:
        """
        Parse the document and yield regions for directive comments.
        """
        parser = Parser()
        settings = get_default_settings(parser)
        # Suppress warnings about unknown directives, etc.
        settings.report_level = 5  # Never report
        doc = new_document(source_path="<sybil>", settings=settings)
        parser.parse(inputstring=document.text, document=doc)

        offsets = line_offsets(text=document.text)

        for node in doc.findall(condition=nodes.comment):
            # Get the comment text
            comment_text = node.astext()

            # Try to match our directive pattern against the comment content
            match = self._directive_pattern.match(string=comment_text)
            if match is None:
                continue

            directive_name = match.group("directive")
            arguments_text = match.group("arguments")

            # Get the line number (1-indexed in docutils)
            line_num = node.line
            if line_num is None:
                continue

            # Convert to 0-indexed
            start_line = line_num - 1

            # Calculate character positions
            if start_line < len(offsets):
                region_start = offsets[start_line]
            else:
                continue

            # Find the end of the comment by looking for the next non-blank,
            # non-indented line or end of document.
            # For simple single-line comments, we find the end of that line.
            # First, find where this comment ends in the source
            comment_lines = comment_text.count("\n") + 1
            end_line = start_line + comment_lines

            if end_line < len(offsets):
                region_end = offsets[end_line]
            else:
                region_end = len(document.text)

            # For simple single-line directives, source is empty
            source = Lexeme(
                text="",
                offset=0,
                line_offset=0,
            )

            lexemes = {
                "directive": directive_name,
                "arguments": arguments_text,
                "source": source,
            }

            yield Region(start=region_start, end=region_end, lexemes=lexemes)
