"""
Code block parsing for Djot.
"""

import re
from collections.abc import Iterable, Sequence
from re import Match, Pattern

from beartype import beartype
from sybil import Document, Region
from sybil.parsers.abstract import AbstractCodeBlockParser
from sybil.parsers.abstract.lexers import strip_prefix
from sybil.parsers.markdown.lexers import DirectiveInHTMLCommentLexer
from sybil.region import Lexeme
from sybil.typing import Evaluator, Lexer

FENCE = re.compile(
    pattern=r"^(?P<prefix>[ \t]*(?:>[ \t]*)*)(?P<fence>`{3,})",
    flags=re.MULTILINE,
)


@beartype
def _match_closes_existing(current: Match[str], existing: Match[str]) -> bool:
    """
    Determine whether the current fence closes the existing block.
    """
    current_fence = current.group("fence")
    existing_fence = existing.group("fence")
    same_type = current_fence[0] == existing_fence[0]
    sufficient_length = len(current_fence) >= len(existing_fence)
    same_prefix = current.group("prefix") == existing.group("prefix")
    return same_type and sufficient_length and same_prefix


@beartype
def _find_container_end(
    *,
    opening: Match[str],
    document: Document,
    info_end: int,
    default_end: int,
) -> int:
    """
    Find where a block closes because its container ends.
    """
    prefix = opening.group("prefix")
    if ">" not in prefix:
        return default_end

    index = opening.end() + info_end
    if index >= default_end:
        return default_end

    text = document.text
    while index < default_end:
        line_end = text.find("\n", index, default_end)
        if line_end == -1:
            line_end = default_end
        else:
            line_end += 1
        line = text[index:line_end]
        if not line.startswith(prefix):
            return index
        index = line_end

    return default_end


class DjotRawFencedCodeBlockLexer:
    """
    A lexer for Djot fenced code blocks that respects block quote boundaries.
    """

    def __init__(
        self,
        info_pattern: Pattern[str] = re.compile(
            pattern=r"$\n", flags=re.MULTILINE
        ),
        mapping: dict[str, str] | None = None,
    ) -> None:
        """
        Initialize the lexer.
        """
        self.info_pattern = info_pattern
        self.mapping = mapping

    def make_region(
        self,
        opening: Match[str],
        document: Document,
        closing: Match[str] | None,
    ) -> Region | None:
        """
        Build a Region for a fenced block.
        """
        if closing is None:
            default_end = len(document.text)
        else:
            default_end = closing.start()

        content = document.text[opening.end() : default_end]
        info = self.info_pattern.match(string=content)
        if info is None:
            return None

        # Check container boundaries regardless of whether closing fence exists
        container_end = _find_container_end(
            opening=opening,
            document=document,
            info_end=info.end(),
            default_end=default_end,
        )

        # Use the earlier of container end or closing fence
        content_end = container_end

        lexemes = info.groupdict()
        lexemes["source"] = Lexeme(
            text=strip_prefix(
                text=document.text[opening.end() + info.end() : content_end],
                prefix=opening.group("prefix"),
            ),
            offset=len(opening.group(0)) + info.end(),
            line_offset=0,
        )
        if self.mapping:
            lexemes = {
                dest: lexemes[source] for source, dest in self.mapping.items()
            }

        # If the container ended before the closing fence, use content_end.
        # Otherwise, include the closing fence in the region.
        if closing is None or content_end < closing.start():
            region_end = content_end
        else:
            region_end = closing.end()
        return Region(
            start=opening.start(),
            end=region_end,
            lexemes=lexemes,
        )

    def __call__(self, document: Document) -> Iterable[Region]:
        """
        Yield regions for Djot fenced code blocks.
        """
        index = 0
        while True:
            opening = FENCE.search(string=document.text, pos=index)
            if opening is None:
                break

            closing: Match[str] | None = None
            search_index = opening.end()
            while True:
                candidate = FENCE.search(
                    string=document.text, pos=search_index
                )
                if candidate is None:
                    break
                search_index = candidate.end()
                if _match_closes_existing(current=candidate, existing=opening):
                    closing = candidate
                    break

            maybe_region = self.make_region(
                opening=opening,
                document=document,
                closing=closing,
            )
            if maybe_region is not None:
                yield maybe_region
                index = maybe_region.end
            else:
                index = opening.end()


class DjotFencedCodeBlockLexer(DjotRawFencedCodeBlockLexer):
    """
    A lexer for Djot fenced code blocks that captures languages.
    """

    def __init__(
        self, language: str, mapping: dict[str, str] | None = None
    ) -> None:
        """
        Initialize the lexer.
        """
        super().__init__(
            info_pattern=re.compile(
                pattern=rf"(?P<language>{language})$\n", flags=re.MULTILINE
            ),
            mapping=mapping,
        )


@beartype
class CodeBlockParser:
    """
    A parser for Djot fenced code blocks.
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
            DjotFencedCodeBlockLexer(
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
        Yield regions for Djot code blocks.
        """
        return self._parser(document)
