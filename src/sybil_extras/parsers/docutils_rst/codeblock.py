"""A code block parser for reStructuredText using the docutils library.

This parser uses docutils to parse RST and extract code blocks.
"""

from collections.abc import Iterable

from beartype import beartype
from docutils import nodes
from docutils.frontend import get_default_settings
from docutils.parsers.rst import Parser
from docutils.utils import new_document
from sybil import Document, Example, Lexeme, Region
from sybil.typing import Evaluator

from sybil_extras.parsers.docutils_rst._line_offsets import line_offsets


@beartype
class CodeBlockParser:
    """A parser for RST code blocks using the docutils library.

    This parser uses docutils to parse RST and extract code blocks
    (``.. code-block::`` directives).

    Args:
        language: The language that this parser should look for.
        evaluator: The evaluator to use for evaluating code blocks in the
            specified language.
    """

    def __init__(
        self,
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
        doc = new_document(source_path="<sybil>", settings=settings)
        parser.parse(inputstring=document.text, document=doc)

        offsets = line_offsets(text=document.text)
        lines = document.text.split(sep="\n")

        for node in doc.findall(condition=nodes.literal_block):
            # Check if this is a code-block (has 'code' in classes)
            node_classes: list[str] = node.get(key="classes", failobj=[])
            if "code" not in node_classes:
                continue

            # Extract the language from classes
            block_language = ""
            for cls in node_classes:
                if cls != "code":
                    block_language = cls
                    break

            # Filter by language if specified
            if self._language is not None and block_language != self._language:
                continue

            # Get content info
            source_content = node.rawsource or node.astext()
            line_count = source_content.count("\n") + 1
            if source_content.endswith("\n"):
                line_count -= 1

            # Get line reference from node or parent
            ref_line = node.line
            if ref_line is None and node.parent is not None:
                ref_line = getattr(node.parent, "line", None)
            if ref_line is None:
                continue

            # Determine content position based on what ref_line points to
            result = self._compute_positions(
                lines=lines,
                ref_line=ref_line,
                line_count=line_count,
                language=block_language,
            )
            if result is None:
                continue

            directive_line, content_start_line, content_end_line = result

            # Calculate byte positions
            region_start = offsets[directive_line - 1]
            source_start = offsets[content_start_line - 1]

            if content_end_line < len(offsets):
                source_end = offsets[content_end_line]
            else:
                source_end = len(document.text)

            # Ensure source has trailing newline
            source_text = source_content
            if not source_text.endswith("\n"):
                source_text = source_text + "\n"

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

            yield Region(
                start=region_start,
                end=region_end,
                parsed=source,
                evaluator=self._evaluator or self.evaluate,
                lexemes=lexemes,
            )

    def _compute_positions(
        self,
        *,
        lines: list[str],
        ref_line: int,
        line_count: int,
        language: str,
    ) -> tuple[int, int, int] | None:
        """Compute directive and content line positions.

        Returns (directive_line, content_start_line, content_end_line)
        as 1-indexed line numbers, or None if not found.
        """
        directive = f".. code-block:: {language}"

        # Check what ref_line points to
        if ref_line < 1 or ref_line > len(lines):
            return None

        line_at_ref = lines[ref_line - 1]
        stripped = line_at_ref.lstrip()

        if stripped.startswith(directive):
            # ref_line is the directive - find content after it
            directive_line = ref_line
            content_start_line = self._find_content_after_directive(
                lines=lines,
                directive_line=directive_line,
            )
            if content_start_line is None:
                return None
            content_end_line = content_start_line + line_count - 1

        elif not stripped:
            # ref_line is blank - content ends before it
            content_end_line = ref_line - 1
            content_start_line = content_end_line - line_count + 1
            found_directive = self._find_directive_before_content(
                lines=lines,
                content_start_line=content_start_line,
                language=language,
            )
            if found_directive is None:
                return None
            directive_line = found_directive

        else:
            # ref_line is content (last line of content)
            content_end_line = ref_line
            content_start_line = content_end_line - line_count + 1
            found_directive = self._find_directive_before_content(
                lines=lines,
                content_start_line=content_start_line,
                language=language,
            )
            if found_directive is None:
                return None
            directive_line = found_directive

        return (directive_line, content_start_line, content_end_line)

    def _find_content_after_directive(
        self,
        *,
        lines: list[str],
        directive_line: int,
    ) -> int | None:
        """Find first content line after directive.

        Returns 1-indexed.
        """
        for i in range(directive_line, len(lines)):
            line = lines[i]
            # Skip blank lines and option lines (starting with :)
            stripped = line.lstrip()
            if not stripped or stripped.startswith(":"):
                continue
            # Skip the directive line itself
            if ".. code-block::" in stripped:
                continue
            # Found content
            return i + 1
        return None

    def _find_directive_before_content(
        self,
        *,
        lines: list[str],
        content_start_line: int,
        language: str,
    ) -> int | None:
        """Find directive line before content.

        Returns 1-indexed.
        """
        directive = f".. code-block:: {language}"
        for i in range(content_start_line - 2, -1, -1):
            line = lines[i].lstrip()
            if line.startswith(directive):
                return i + 1
            # Stop if we hit non-blank, non-option content
            if line and not line.startswith(":"):
                break
        return None
