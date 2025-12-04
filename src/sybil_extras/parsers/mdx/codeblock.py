"""
A code block parser for MDX with attribute support.
"""

import re
from collections.abc import Iterable

from beartype import beartype
from sybil import Document, Region
from sybil.parsers.abstract import AbstractCodeBlockParser
from sybil.parsers.markdown.lexers import (
    DirectiveInHTMLCommentLexer,
    RawFencedCodeBlockLexer,
)
from sybil.typing import Evaluator, Lexer

_INFO_LINE_PATTERN = re.compile(
    pattern=r"(?P<language>[^\s`]+)(?P<attributes>(?:[ \t]+[^\n]*?)?)$\n",
    flags=re.MULTILINE,
)

_ATTRIBUTE_PATTERN = re.compile(
    pattern=r"""
    (?P<name>[A-Za-z0-9_.:-]+)
    \s*=\s*
    (?P<quote>["'])
    (?P<value>.*?)
    (?P=quote)
    """,
    flags=re.VERBOSE,
)


@beartype
class CodeBlockParser:
    """
    A parser for MDX fenced code blocks that preserves attributes.
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
        lexers: list[Lexer] = [
            RawFencedCodeBlockLexer(
                info_pattern=_INFO_LINE_PATTERN,
                mapping={
                    "language": "arguments",
                    "attributes": "attributes_raw",
                    "source": "source",
                },
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
        Yield regions for code blocks, parsing any MDX attributes.
        """
        for region in self._parser(document):
            raw_attributes = region.lexemes.get("attributes_raw")
            parsed_attributes = self._parse_attributes(
                attr_string=raw_attributes
                if isinstance(raw_attributes, str)
                else ""
            )
            region.lexemes["attributes"] = parsed_attributes
            yield region

    @staticmethod
    def _parse_attributes(attr_string: str) -> dict[str, str]:
        """
        Parse key/value pairs from the info line attribute string.
        """
        if not attr_string:
            return {}

        attributes: dict[str, str] = {}
        for match in _ATTRIBUTE_PATTERN.finditer(string=attr_string):
            name = match.group("name")
            value = match.group("value")
            attributes[name] = value
        return attributes
