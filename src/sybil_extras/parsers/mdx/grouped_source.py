"""
A group parser for MDX.
"""

import re

from beartype import beartype
from sybil.parsers.markdown.lexers import DirectiveInHTMLCommentLexer
from sybil.typing import Evaluator

from sybil_extras.parsers.abstract.grouped_source import (
    AbstractGroupedSourceParser,
)


@beartype
class GroupedSourceParser(AbstractGroupedSourceParser):
    """
    A code block group parser for MDX.
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
            directive: The directive used inside HTML comments.
            evaluator: Evaluator for the combined region.
            pad_groups: Whether to pad grouped blocks with blank lines.
        """
        lexers = [
            DirectiveInHTMLCommentLexer(
                directive=re.escape(pattern=directive),
            ),
        ]
        super().__init__(
            lexers=lexers,
            evaluator=evaluator,
            directive=directive,
            pad_groups=pad_groups,
        )
