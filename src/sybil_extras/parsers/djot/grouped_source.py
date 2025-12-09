"""
A group parser for Djot.
"""

import re

from beartype import beartype
from sybil.typing import Evaluator

from sybil_extras.parsers.abstract.grouped_source import (
    AbstractGroupedSourceParser,
)
from sybil_extras.parsers.djot.lexers import DirectiveInDjotCommentLexer


@beartype
class GroupedSourceParser(AbstractGroupedSourceParser):
    """
    A code block group parser for Djot.
    """

    def __init__(
        self,
        *,
        directive: str,
        evaluator: Evaluator,
        pad_groups: bool,
    ) -> None:
        """
        Args:
            directive: The name of the directive to use for grouping.
            evaluator: The evaluator to use for evaluating the combined region.
            pad_groups: Whether to pad groups with empty lines.
                This is useful for error messages that reference line numbers.
                However, this is detrimental to commands that expect the file
                to not have a bunch of newlines in it, such as formatters.
        """
        lexers = [
            DirectiveInDjotCommentLexer(
                directive=re.escape(pattern=directive),
            ),
        ]
        super().__init__(
            lexers=lexers,
            evaluator=evaluator,
            directive=directive,
            pad_groups=pad_groups,
        )
