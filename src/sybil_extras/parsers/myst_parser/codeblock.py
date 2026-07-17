"""A code block parser for MyST using the myst-parser library.

This parser uses the myst-parser library, which extends markdown-it-py
with MyST-specific extensions.
"""

import re
from collections.abc import Iterable

from beartype import beartype
from markdown_it.renderer import RendererHTML
from markdown_it.token import Token
from myst_parser.config.main import MdParserConfig
from myst_parser.parsers.mdit import create_md_parser
from sybil import Document, Example, Lexeme, Region
from sybil.typing import Evaluator

from sybil_extras.parsers._line_offsets import line_offsets
from sybil_extras.parsers.myst_parser.sphinx_jinja2 import (
    parse_options_and_body,
)

# Pattern to match an ``invisible-code-block`` directive inside an HTML
# comment. Mirrors ``sybil.parsers.markdown.codeblock.CodeBlockParser``
# which registers ``DirectiveInHTMLCommentLexer`` with
# ``directive=r'(invisible-)?code(-block)?'`` and ``arguments='.+'``.
_INVISIBLE_CODE_BLOCK_PATTERN = re.compile(
    pattern=r"^[ \t]*<!--+\s*(?:;\s*)?(?:invisible-)?code(?:-block)?:?"
    r"[ \t]*(?P<language>\S+)[ \t]*"
    r"(?:\n|(?=--+>))",
)
_HTML_COMMENT_END_PATTERN = re.compile(pattern=r"--+>")


@beartype
class CodeBlockParser:
    """A parser for MyST fenced code blocks using the myst-parser
    library.

    This parser uses the myst-parser library, which extends
    markdown-it-py with MyST-specific syntax support.

    Args:
        language: The language that this parser should look for.
        evaluator: The evaluator to use for evaluating code blocks in the
            specified language.
    """

    def __init__(
        self,
        *,
        language: str | None = None,
        evaluator: Evaluator | None = None,
    ) -> None:
        """Initialize the parser."""
        self._language = language
        self._evaluator = evaluator

    def evaluate(self, example: Example) -> None:
        """Evaluate method used when no evaluator is provided.

        This matches the behavior of Sybil's AbstractCodeBlockParser.
        Override this method to provide custom evaluation logic.
        """
        raise NotImplementedError

    def __call__(self, document: Document) -> Iterable[Region]:
        """Parse the document and yield regions for each fenced code
        block.
        """
        config = MdParserConfig()
        md = create_md_parser(config=config, renderer=RendererHTML)
        # Disable the indented code block rule so that fenced code blocks
        # inside indented sections are still recognized as fences.
        # This matches Sybil's regex-based behavior which allows fenced
        # code blocks with a whitespace prefix.
        md.disable(names="code")
        tokens = md.parse(src=document.text)
        offsets = line_offsets(text=document.text)

        for token in tokens:
            if token.type == "html_block":
                region = self._html_comment_region(
                    token=token,
                    document=document,
                    offsets=offsets,
                )
            elif token.type == "fence":
                region = self._fence_region(
                    token=token,
                    document=document,
                    offsets=offsets,
                )
            else:
                continue
            if region is not None:
                yield region

    def _fence_region(
        self,
        *,
        token: Token,
        document: Document,
        offsets: list[int],
    ) -> Region | None:
        """Build a region for a fenced code block token."""
        if token.map is None:  # pragma: no cover
            raise ValueError(token)

        # Extract just the language from the info string. The info string
        # can contain extra metadata (e.g., "python title=..."). MyST
        # directive-style blocks use the format "{directive} language"
        # (e.g., "{code-block} python"), where the actual language is the
        # second word.
        words = token.info.strip().split()
        is_directive = bool(words and words[0].startswith("{"))
        if not words:
            block_language = ""
        elif is_directive:
            block_language = words[1] if len(words) > 1 else ""
        else:
            block_language = words[0]

        if self._language is not None and block_language != self._language:
            return None

        start_line, end_line = token.map
        region_start = offsets[start_line]
        if end_line < len(offsets):
            region_end = offsets[end_line] - 1
        else:
            region_end = len(document.text)

        source_text = token.content
        removed_prefix = ""
        if is_directive:
            _, source_text = parse_options_and_body(content=token.content)
            source_length = len(source_text)
            removed_length = len(token.content) - source_length
            removed_prefix = token.content[:removed_length]

        source_start_line = start_line + 1 + removed_prefix.count("\n")
        if source_start_line < len(offsets):
            opening_fence_end = offsets[source_start_line]
        else:
            opening_fence_end = len(document.text)
        source_offset = opening_fence_end - region_start

        source = Lexeme(
            text=source_text,
            offset=source_offset,
            line_offset=0,
        )
        lexemes = {"language": block_language, "source": source}
        return Region(
            start=region_start,
            end=region_end,
            parsed=source,
            evaluator=self._evaluator or self.evaluate,
            lexemes=lexemes,
        )

    def _html_comment_region(
        self,
        *,
        token: Token,
        document: Document,
        offsets: list[int],
    ) -> Region | None:
        """Build a region for an ``invisible-code-block`` HTML comment.

        Returns ``None`` if the HTML comment is not an invisible code
        block, or if the language filter does not match.
        """
        if token.map is None:  # pragma: no cover
            raise ValueError(token)
        content = token.content
        match = _INVISIBLE_CODE_BLOCK_PATTERN.match(string=content)
        if match is None:
            return None
        block_language = match.group("language")
        if self._language is not None and block_language != self._language:
            return None
        end_match = _HTML_COMMENT_END_PATTERN.search(
            string=content,
            pos=match.end(),
        )
        if end_match is None:
            return None

        start_line, end_line = token.map
        region_start = offsets[start_line]
        if end_line < len(offsets):
            region_end = offsets[end_line]
        else:
            region_end = len(document.text)

        source = Lexeme(
            text=content[match.end() : end_match.start()],
            offset=match.end(),
            line_offset=content[: match.end()].count("\n") - 1,
        )
        lexemes = {"language": block_language, "source": source}
        return Region(
            start=region_start,
            end=region_end,
            parsed=source,
            evaluator=self._evaluator or self.evaluate,
            lexemes=lexemes,
        )
