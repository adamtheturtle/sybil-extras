"""
A code block parser for MDX with attribute support.
"""

import re
from collections.abc import Iterable

from beartype import beartype
from sybil import Document, Region
from sybil.parsers.markdown.lexers import RawFencedCodeBlockLexer
from sybil.typing import Evaluator


@beartype
class CodeBlockParser:
    """A parser for MDX code blocks with attributes.

    Parses code blocks in the format:
    ```language attr1="value1" attr2="value2"
    code content
    ```

    Supports attributes like:
    - title: filename or title for the code block
    - group: group identifier for related code blocks
    """

    def __init__(
        self,
        *,
        language: str | None = None,
        evaluator: Evaluator,
    ) -> None:
        """
        Args:
            language: The language to match (e.g., "python", "JavaScript").
                If None, matches all languages.
            evaluator: The evaluator to use for evaluating the code block.
        """
        self._language = language
        self._evaluator = evaluator

        # Create a pattern to match the info line with optional attributes
        if language:
            escaped_lang = re.escape(pattern=language)
            info_pattern = re.compile(
                pattern=rf"(?P<language>{escaped_lang})(?P<attributes>[^\n]*?)$\n",
                flags=re.MULTILINE,
            )
        else:
            info_pattern = re.compile(
                pattern=r"(?P<language>\w+)(?P<attributes>[^\n]*?)$\n",
                flags=re.MULTILINE,
            )

        self._lexer = RawFencedCodeBlockLexer(
            info_pattern=info_pattern,
            mapping=None,
        )

    def __call__(self, document: Document) -> Iterable[Region]:
        """
        Parse the document and yield regions for code blocks.
        """
        for region in self._lexer(document):
            # Check if the language matches
            lang = region.lexemes.get("language")
            if self._language and lang != self._language:
                continue

            # Parse attributes from the attributes string
            attr_string = region.lexemes.get("attributes", "")
            attributes = self._parse_attributes(attr_string=attr_string)

            # Get the source lexeme
            source_lexeme = region.lexemes["source"]

            # Update the region with parsed data
            region.parsed = source_lexeme
            region.evaluator = self._evaluator
            region.lexemes["attributes"] = attributes

            yield region

    @staticmethod
    def _parse_attributes(attr_string: str) -> dict[str, str]:
        """Parse attributes from the fence line.

        Supports formats like:
        - title="hello.python"
        - group="my-group"
        - key="value" key2="value2"
        """
        attributes: dict[str, str] = {}

        # Pattern to match key="value" pairs
        attr_pattern = re.compile(pattern=r'(\w+)="([^"]*)"')

        for match in attr_pattern.finditer(string=attr_string):
            key = match.group(1)
            value = match.group(2)
            attributes[key] = value

        return attributes
