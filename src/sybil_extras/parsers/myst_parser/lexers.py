"""Lexers for MyST using the myst-parser library.

These lexers use the myst-parser library, which extends markdown-it-py
with MyST-specific extensions including percent-style comments.
"""

import re
from collections.abc import Iterable

from beartype import beartype
from markdown_it.renderer import RendererHTML
from myst_parser.config.main import MdParserConfig
from myst_parser.parsers.mdit import create_md_parser
from sybil import Document, Lexeme, Region

from sybil_extras.parsers._line_offsets import line_offsets


@beartype
class DirectiveInHTMLCommentLexer:
    """A lexer for directives embedded in HTML comments using
    myst-parser.

    This lexer finds HTML comments that contain directives in the
    format:
    ``<!--- directive: arguments -->`` or
    ``<!-- directive: arguments -->``.

    It yields Region objects with the following lexemes:

    - ``directive`` as a :class:`str`.
    - ``arguments`` as a :class:`str`.
    - ``source`` as a :class:`~sybil.Lexeme` (empty for single-line
      directives).

    Args:
        directive: A string containing a regular expression pattern to
            match directive names.
        arguments: A string containing a regular expression pattern to
            match directive arguments.
    """

    def __init__(
        self,
        *,
        directive: str,
        arguments: str = ".*?",
    ) -> None:
        """Initialize the lexer."""
        self._directive_pattern = re.compile(
            pattern=rf"^[ \t]*<!--+\s*(?:;\s*)?(?P<directive>{directive})"
            rf":?\s*(?P<arguments>{arguments})\s*"
            rf"(?:--+>|$)",
            flags=re.MULTILINE,
        )

    def __call__(self, document: Document) -> Iterable[Region]:
        """Parse the document and yield regions for directive
        comments.
        """
        config = MdParserConfig()
        md = create_md_parser(config=config, renderer=RendererHTML)
        md.disable(names="code")
        tokens = md.parse(src=document.text)
        offsets = line_offsets(text=document.text)

        for token in tokens:
            if token.type != "html_block":
                continue

            if token.map is None:  # pragma: no cover
                # map is always set for html_block tokens.
                raise ValueError(token)

            start_line, end_line = token.map

            region_start = offsets[start_line]
            if end_line < len(offsets):
                region_end = offsets[end_line]
            else:
                region_end = len(document.text)

            content = token.content
            match = self._directive_pattern.match(string=content)
            if match is None:
                continue

            directive_name = match.group("directive")
            arguments = match.group("arguments")

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

            yield Region(
                start=region_start,
                end=region_end,
                lexemes=lexemes,
            )


@beartype
class DirectiveInPercentCommentLexer:
    """A lexer for directives embedded in percent-style comments using
    myst-parser.

    This lexer finds percent-style comments that contain directives
    in the format: ``% directive: arguments``.

    The myst-parser library parses percent comments as
    ``myst_line_comment`` tokens, giving proper AST-based detection
    instead of regex matching.

    It yields Region objects with the following lexemes:

    - ``directive`` as a :class:`str`.
    - ``arguments`` as a :class:`str`.
    - ``source`` as a :class:`~sybil.Lexeme` (empty for single-line
      directives).

    Args:
        directive: A string containing a regular expression pattern to
            match directive names.
        arguments: A string containing a regular expression pattern to
            match directive arguments.
    """

    def __init__(
        self,
        *,
        directive: str,
        arguments: str = ".*?",
    ) -> None:
        """Initialize the lexer."""
        self._directive_pattern = re.compile(
            pattern=rf"^\s*(?P<directive>{directive})"
            rf":?\s*(?P<arguments>{arguments})\s*$",
        )

    def __call__(self, document: Document) -> Iterable[Region]:
        """Parse the document and yield regions for directive
        comments.
        """
        config = MdParserConfig()
        md = create_md_parser(config=config, renderer=RendererHTML)
        md.disable(names="code")
        tokens = md.parse(src=document.text)
        offsets = line_offsets(text=document.text)

        for token in tokens:
            if token.type != "myst_line_comment":
                continue

            if token.map is None:  # pragma: no cover
                # map is always set for myst_line_comment tokens.
                raise ValueError(token)

            start_line, end_line = token.map

            region_start = offsets[start_line]
            if end_line < len(offsets):
                region_end = offsets[end_line]
            else:
                region_end = len(document.text)

            content = token.content
            match = self._directive_pattern.match(string=content)
            if match is None:
                continue

            directive_name = match.group("directive")
            arguments = match.group("arguments")

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

            yield Region(
                start=region_start,
                end=region_end,
                lexemes=lexemes,
            )
