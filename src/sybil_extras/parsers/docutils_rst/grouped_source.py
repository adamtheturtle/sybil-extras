"""A group parser for reStructuredText using the docutils library.

This parser uses the docutils library instead of regex.
"""

import re

from beartype import beartype
from sybil.typing import Evaluator

from sybil_extras.parsers.abstract.grouped_source import (
    AbstractGroupedSourceParser,
)
from sybil_extras.parsers.docutils_rst.lexers import DirectiveInCommentLexer


@beartype
class GroupedSourceParser(AbstractGroupedSourceParser):
    """A code block group parser for reStructuredText.

    This parser uses the docutils library to find RST comments
    containing group directives.
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
            DirectiveInCommentLexer(
                directive=re.escape(pattern=directive),
            ),
        ]
        super().__init__(
            lexers=lexers,
            evaluator=evaluator,
            directive=directive,
            pad_groups=pad_groups,
        )
