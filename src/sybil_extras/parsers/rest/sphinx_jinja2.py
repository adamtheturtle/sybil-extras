"""
A parser for Sphinx jinja2 blocks in reST.
"""

import re
from collections.abc import Iterable

from sybil import Document, Region
from sybil.parsers.abstract.lexers import LexerCollection
from sybil.parsers.rest.lexers import DirectiveLexer
from sybil.typing import Evaluator


class SphinxJinja2Parser:
    """
    A parser for Sphinx jinja2 blocks in reST.
    """

    def __init__(
        self,
        *,
        evaluator: Evaluator,
    ) -> None:
        """
        Args:
            evaluator: The evaluator to use for evaluating the combined region.
        """
        directive = "jinja"
        lexers = [
            DirectiveLexer(directive=re.escape(pattern=directive)),
        ]
        self._lexers: LexerCollection = LexerCollection(lexers)
        self._evaluator = evaluator

    def __call__(self, document: Document) -> Iterable[Region]:
        """
        Parse the document for sphinx-jinja2 blocks.
        """
        for region in self._lexers(document):
            region.parsed = region.lexemes["source"]
            region.evaluator = self._evaluator
            yield region
