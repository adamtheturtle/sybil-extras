"""A reStructuredText code block parser.

This wraps Sybil's stock reStructuredText code block parser to record the
structural placement of content within each region (see
:mod:`sybil_extras.parsers.rest._content_placement`), so that the
code block writer can insert content into empty blocks without knowing
any reStructuredText-specific formatting.
"""

from collections.abc import Iterable

import sybil.parsers.rest
from beartype import beartype
from sybil import Document, Region
from sybil.typing import Evaluator

from sybil_extras.parsers.rest._content_placement import (
    attach_content_placement,
)


@beartype
class CodeBlockParser:
    """A parser for reStructuredText code blocks."""

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
        self._parser = sybil.parsers.rest.CodeBlockParser(
            language=language,
            evaluator=evaluator,
        )

    def __call__(self, document: Document) -> Iterable[Region]:
        """Yield regions for code blocks, recording content placement."""
        for region in self._parser(document):
            attach_content_placement(region=region)
            yield region
