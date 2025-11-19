"""
A parser that groups all code blocks in a Markdown document.
"""

from sybil.typing import Evaluator

from sybil_extras.parsers.abstract.group_all import AbstractGroupAllParser


class GroupAllParser(AbstractGroupAllParser):
    """
    A parser that groups all code blocks in a document without markup.
    """

    def __init__(
        self,
        *,
        evaluator: Evaluator,
        pad_groups: bool,
    ) -> None:
        """
        Args:
            evaluator: The evaluator to use for evaluating the combined region.
            pad_groups: Whether to pad groups with empty lines.
                This is useful for error messages that reference line numbers.
                However, this is detrimental to commands that expect the file
                to not have a bunch of newlines in it, such as formatters.
        """
        super().__init__(evaluator=evaluator, pad_groups=pad_groups)
