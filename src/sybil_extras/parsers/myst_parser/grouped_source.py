"""A group parser for MyST using the myst-parser library.

This parser uses the myst-parser library instead of regex.
"""

import re

from beartype import beartype
from sybil.typing import Evaluator

from sybil_extras.parsers.abstract.grouped_source import (
    AbstractGroupedSourceParser,
)
from sybil_extras.parsers.myst_parser.lexers import (
    DirectiveInHTMLCommentLexer,
    DirectiveInPercentCommentLexer,
)


@beartype
class GroupedSourceParser(AbstractGroupedSourceParser):
    """A code block group parser for MyST.

    This parser uses the myst-parser library to find both HTML comments
    and percent-style comments containing group directives.
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
            evaluator: The evaluator to use for evaluating the combined
        region.
            pad_groups: Whether to pad groups with empty lines.
                This is useful for error messages that reference line
        numbers.
                However, this is detrimental to commands that expect the
        file
                to not have a bunch of newlines in it, such as
        formatters.
        """
        lexers = [
            DirectiveInPercentCommentLexer(
                directive=re.escape(pattern=directive),
            ),
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
