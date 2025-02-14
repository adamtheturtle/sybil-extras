"""
A group parser for Markdown.
"""

from sybil.parsers.markdown.lexers import DirectiveInHTMLCommentLexer
from sybil.typing import Evaluator

from sybil_extras.parsers.abstract.grouped_code_block import (
    AbstractGroupedCodeBlockParser,
)


class GroupedCodeBlockParser(AbstractGroupedCodeBlockParser):
    """
    A code block group parser for Markdown.
    """

    def __init__(self, directive: str, evaluator: Evaluator) -> None:
        """
        Args:
            directive: The name of the directive to use for grouping.
        """
        lexers = [
            DirectiveInHTMLCommentLexer(directive=directive),
        ]
        super().__init__(lexers=lexers, evaluator=evaluator)
