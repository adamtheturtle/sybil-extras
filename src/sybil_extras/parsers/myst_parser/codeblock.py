"""A code block parser for MyST using the myst-parser library.

This parser uses the myst-parser library, which extends markdown-it-py
with MyST-specific extensions.
"""

from collections.abc import Iterable

from beartype import beartype
from markdown_it.renderer import RendererHTML
from myst_parser.config.main import MdParserConfig
from myst_parser.parsers.mdit import create_md_parser
from sybil import Document, Example, Lexeme, Region
from sybil.typing import Evaluator

from sybil_extras.parsers.abstract._line_offsets import line_offsets


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
            if token.type != "fence":
                continue

            # MarkdownIt always provides map for fence tokens.
            if token.map is None:  # pragma: no cover
                # This should never happen; map is always set for fence tokens.
                raise ValueError(token)

            # Extract just the language from the info string.
            # The info string can contain extra metadata
            # (e.g., "python title=...").
            info = token.info.strip()
            block_language = info.split()[0] if info else ""

            # Filter by language if specified
            if self._language is not None and block_language != self._language:
                continue

            start_line, end_line = token.map

            # Calculate character positions
            region_start = offsets[start_line]

            # end_line is exclusive in MarkdownIt, pointing to the line
            # after the closing fence. We want the region to end at the
            # end of the closing fence line, not including the trailing
            # newline. This matches Sybil's regex-based behavior.
            if end_line < len(offsets):
                # Get the start of the line after the block
                next_line_start = offsets[end_line]
                # The region end excludes the trailing newline after the
                # closing fence.
                region_end = next_line_start - 1
            else:
                region_end = len(document.text)

            # The source content is in token.content
            # We need to calculate the offset within the region where
            # the source starts.
            if start_line + 1 < len(offsets):
                opening_fence_end = offsets[start_line + 1]
            else:
                # Edge case: document ends without a newline after the
                # fence.
                opening_fence_end = len(document.text)
            opening_fence_line = document.text[region_start:opening_fence_end]
            source_offset = len(opening_fence_line)

            source = Lexeme(
                text=token.content,
                offset=source_offset,
                # line_offset is the number of newlines in the opening
                # delimiter minus 1. For Markdown fenced code blocks,
                # the opening line (e.g., "```python\n") has exactly one
                # newline, so line_offset is always 0.
                line_offset=0,
            )

            lexemes = {"language": block_language, "source": source}

            yield Region(
                start=region_start,
                end=region_end,
                parsed=source,
                evaluator=self._evaluator or self.evaluate,
                lexemes=lexemes,
            )
