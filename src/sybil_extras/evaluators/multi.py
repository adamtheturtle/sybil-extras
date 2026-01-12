"""
Use multiple evaluators.
"""

from collections.abc import Sequence

from beartype import beartype
from sybil import Example
from sybil.typing import Evaluator


@beartype
class MultiEvaluator:
    """
    Run multiple evaluators.
    """

    def __init__(self, evaluators: Sequence[Evaluator]) -> None:
        """
        Run multiple evaluators.
        """
        self._evaluators = evaluators

    def __call__(self, example: Example) -> str | None:
        """
        Run all evaluators.
        """
        for evaluator in self._evaluators:
            result = evaluator(example)
            if result is not None:
                return result
        return None
