"""A parser that groups all code blocks in a reStructuredText document.

This parser uses the docutils library.
"""

from beartype import beartype
from sybil.typing import Evaluator

from sybil_extras.parsers.abstract.group_all import AbstractGroupAllParser

_NO_PAD_SEPARATOR_LINES = 2


@beartype
class GroupAllParser(AbstractGroupAllParser):
    """
    A parser that groups all code blocks in a document without
    markup.
    """

    def __init__(
        self,
        *,
        evaluator: Evaluator,
        pad_groups: bool,
    ) -> None:
        """
        Args:
            evaluator: The evaluator to use for evaluating the
        combined region.
            pad_groups: Whether to pad groups with empty lines.
        """
        super().__init__(
            evaluator=evaluator,
            pad_groups=pad_groups,
            no_pad_separator_lines=_NO_PAD_SEPARATOR_LINES,
        )
