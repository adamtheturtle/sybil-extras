"""
No-op Evaluator.
"""

from sybil.example import Example


class NoOpEvaluator:
    """An evaluator that does nothing.

    This is useful for testing and debugging.
    """

    def __call__(self, _: Example) -> None:
        """
        Do nothing.
        """
