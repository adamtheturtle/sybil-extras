"""A code block parser for reStructuredText using the docutils library.

This parser uses docutils to parse RST and extract code blocks.
"""

import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from beartype import beartype
from docutils import nodes
from docutils.frontend import get_default_settings
from docutils.parsers.rst import Parser
from docutils.utils import new_document
from sybil import Document, Example, Lexeme, Region
from sybil.typing import Evaluator

from sybil_extras.parsers._line_offsets import line_offsets

_INVISIBLE_CODE_COMMENT_PATTERN = re.compile(
    pattern=r"^invisible-code-block:\s*(?P<language>.*?)\s*$",
)


@beartype
class CodeBlockParser:
    """A parser for RST code blocks using the docutils library.

    This parser uses docutils to parse RST and extract code blocks
    (``.. code-block::`` and ``.. code::`` directives).

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
        """Parse the document and yield regions for each code block."""
        parser = Parser()
        settings = get_default_settings(parser)
        # Suppress warnings about unknown directives, etc.
        settings.report_level = 5  # Never report
        # Prevent SEVERE messages (e.g. from .. include:: directives with
        # relative paths) from raising SystemMessage exceptions.
        settings.halt_level = 5  # Never halt
        doc = new_document(source_path="<sybil>", settings=settings)
        parser.parse(inputstring=document.text, document=doc)

        offsets = line_offsets(text=document.text)
        lines = document.text.split(sep="\n")

        for node in doc.findall(condition=nodes.literal_block):
            region = self._process_node(
                node=node,
                document=document,
                offsets=offsets,
                lines=lines,
            )
            if region is not None:
                yield region

        for comment_node in doc.findall(condition=nodes.comment):
            region = self._process_invisible_comment_node(
                node=comment_node,
                document=document,
                offsets=offsets,
                lines=lines,
            )
            if region is not None:
                yield region

    def _process_node(
        self,
        *,
        node: nodes.literal_block,
        document: Document,
        offsets: list[int],
        lines: Sequence[str],
    ) -> Region | None:
        """Process a single literal_block node into a Region.

        Returns None if the node should be skipped.
        """
        # Check if this is a code-block (has 'code' in classes)
        node_classes: list[str] = node.get(key="classes", failobj=[])
        if "code" not in node_classes:
            return None

        # Extract the language from classes
        block_language = ""
        for cls in node_classes:
            if cls != "code":
                block_language = cls
                break

        # Filter by language if specified
        if self._language is not None and block_language != self._language:
            return None

        # Get content info
        source_content = node.rawsource or node.astext()
        line_count = source_content.count("\n") + 1

        # Get line reference from node or parent
        ref_line = node.line
        if ref_line is None and node.parent is not None:
            ref_line = getattr(node.parent, "line", None)
        if ref_line is None:  # pragma: no cover
            # Code blocks with the 'code' class always have a line
            # reference via node.line or node.parent.line.
            msg = "Code block node has no line reference"
            raise ValueError(msg)

        # Determine content position based on what ref_line points to
        positions = _compute_positions(
            lines=lines,
            ref_line=ref_line,
            line_count=line_count,
            language=block_language,
        )

        # Calculate byte positions
        region_start = offsets[positions.directive_line - 1]
        source_start = offsets[positions.content_start_line - 1]

        if positions.content_end_line < len(offsets):
            source_end = offsets[positions.content_end_line]
        else:
            source_end = len(document.text)

        # Preserve trailing blank lines (stripped by docutils from rawsource)
        # and ensure at least one trailing newline.
        source_text = source_content.rstrip("\n") + "\n" * (
            1 + positions.trailing_blank_lines
        )

        region_end = source_end
        source_offset = source_start - region_start

        opening_text = document.text[region_start:source_start]
        line_offset = max(opening_text.count("\n") - 1, 0)

        source = Lexeme(
            text=source_text,
            offset=source_offset,
            line_offset=line_offset,
        )

        lexemes = {"language": block_language, "source": source}

        return Region(
            start=region_start,
            end=region_end,
            parsed=source,
            evaluator=self._evaluator or self.evaluate,
            lexemes=lexemes,
        )

    def _process_invisible_comment_node(
        self,
        *,
        node: nodes.comment,
        document: Document,
        offsets: list[int],
        lines: Sequence[str],
    ) -> Region | None:
        """Process a comment node for single-colon invisible-code-block.

        Returns None if the node doesn't match the directive pattern.
        """
        comment_text = node.astext()
        first_line, *rest_lines = comment_text.split(sep="\n")
        match = _INVISIBLE_CODE_COMMENT_PATTERN.match(string=first_line)
        if match is None:
            return None

        block_language = match.group("language")

        if self._language is not None and block_language != self._language:
            return None

        # Extract code lines (skip leading blanks).
        # Docutils strips trailing blanks from comment ``astext()``;
        # trailing blank lines are preserved via
        # positions.trailing_blank_lines.
        code_lines: list[str] = []
        found_content = False
        for line in rest_lines:
            if not found_content and not line.strip():
                continue
            found_content = True
            code_lines.append(line)

        source_content = "\n".join(code_lines)
        line_count = len(code_lines)

        ref_line = node.line
        if ref_line is None:  # pragma: no cover
            msg = "Comment node has no line reference"
            raise ValueError(msg)

        positions = _compute_positions(
            lines=lines,
            ref_line=ref_line,
            line_count=line_count,
            language=block_language,
        )

        region_start = offsets[positions.directive_line - 1]
        source_start = offsets[positions.content_start_line - 1]

        if positions.content_end_line < len(offsets):
            source_end = offsets[positions.content_end_line]
        else:
            source_end = len(document.text)

        # Preserve trailing blank lines (stripped by docutils from astext)
        # and ensure at least one trailing newline.
        source_text = source_content.rstrip("\n") + "\n" * (
            1 + positions.trailing_blank_lines
        )
        region_end = source_end
        source_offset = source_start - region_start

        opening_text = document.text[region_start:source_start]
        line_offset = max(opening_text.count("\n") - 1, 0)

        source = Lexeme(
            text=source_text,
            offset=source_offset,
            line_offset=line_offset,
        )

        lexemes = {"language": block_language, "source": source}

        return Region(
            start=region_start,
            end=region_end,
            parsed=source,
            evaluator=self._evaluator or self.evaluate,
            lexemes=lexemes,
        )


@dataclass(frozen=True)
class _Positions:
    """Directive and content line positions (1-indexed)."""

    directive_line: int
    content_start_line: int
    content_end_line: int
    trailing_blank_lines: int = 0


@beartype
def _directive_prefixes(*, language: str) -> tuple[str, ...]:
    """Build directive prefixes for ``code-block``, ``code``, and single-
    colon
    ``invisible-code-block``.
    """
    double_colon = (".. code-block::", ".. code::")
    prefixes = [f"{d} {language}".rstrip() for d in double_colon]
    # Single-colon (comment-based) invisible-code-block
    if language:
        prefixes.append(f".. invisible-code-block: {language}")
    else:
        prefixes.append(".. invisible-code-block:")
    return tuple(prefixes)


@beartype
def _compute_positions(
    *,
    lines: Sequence[str],
    ref_line: int,
    line_count: int,
    language: str,
) -> _Positions:
    """Compute directive and content line positions.

    Returns 1-indexed line numbers.
    """
    prefixes = _directive_prefixes(language=language)

    line_at_ref = lines[ref_line - 1]
    stripped = line_at_ref.lstrip()

    if any(stripped.startswith(p) for p in prefixes):
        # ref_line is the directive - find content after it
        directive_line = ref_line
        content_start_line = _find_content_after_directive(
            lines=lines,
            directive_line=directive_line,
        )
        content_end_line = content_start_line + line_count - 1
        trailing_blank_lines = 0

    elif not stripped:
        # ref_line is blank - content ends before it.
        # Docutils may point ref_line to a blank line that is several
        # lines after the actual code content, with trailing blank lines
        # in between (which docutils strips from rawsource/astext).
        content_end_line = ref_line - 1
        # Find the actual last non-blank content line.
        actual_last_content = content_end_line
        while (
            actual_last_content > 0
            and not lines[actual_last_content - 1].strip()
        ):
            actual_last_content -= 1
        trailing_blank_lines = content_end_line - actual_last_content
        content_start_line = actual_last_content - line_count + 1
        directive_line = _find_directive_before_content(
            lines=lines,
            content_start_line=content_start_line,
            language=language,
        )

    else:
        # ref_line is content (last line of content)
        content_end_line = ref_line
        content_start_line = content_end_line - line_count + 1
        trailing_blank_lines = 0
        directive_line = _find_directive_before_content(
            lines=lines,
            content_start_line=content_start_line,
            language=language,
        )

    return _Positions(
        directive_line=directive_line,
        content_start_line=content_start_line,
        content_end_line=content_end_line,
        trailing_blank_lines=trailing_blank_lines,
    )


@beartype
def _find_content_after_directive(
    *,
    lines: Sequence[str],
    directive_line: int,
) -> int:
    """Find first content line after directive.

    Returns 1-indexed.
    """
    return next(
        line_idx + 1
        for line_idx in range(directive_line, len(lines))
        if lines[line_idx].lstrip()
    )


@beartype
def _find_directive_before_content(
    *,
    lines: Sequence[str],
    content_start_line: int,
    language: str,
) -> int:
    """Find directive line before content.

    Returns 1-indexed.
    """
    prefixes = _directive_prefixes(language=language)
    return next(
        line_idx + 1
        for line_idx in range(content_start_line - 2, -1, -1)
        if any(
            lines[line_idx].lstrip().startswith(prefix) for prefix in prefixes
        )
    )
