"""
A parser for Sphinx jinja2 blocks in reST.
"""

import re

from sybil.parsers.abstract.codeblock import AbstractCodeBlockParser
from sybil.parsers.abstract.lexers import LexerCollection
from sybil.parsers.rest.lexers import DirectiveInCommentLexer
from sybil.typing import Evaluator


class SphinxJinja2Parser(AbstractCodeBlockParser):
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
            pad_groups: Whether to pad groups with empty lines.
                This is useful for error messages that reference line numbers.
                However, this is detrimental to commands that expect the file
                to not have a bunch of newlines in it, such as formatters.
        """
        directive = "jinja"
        lexers = [
            DirectiveInCommentLexer(directive=re.escape(pattern=directive)),
        ]
        self.lexers: LexerCollection = LexerCollection(lexers)
        self.language = ""
        self._evaluator = evaluator
