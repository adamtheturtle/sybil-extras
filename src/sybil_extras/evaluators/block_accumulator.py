"""
Block accumulator evaluator.
"""

from beartype import beartype
from sybil.example import Example


@beartype
class BlockAccumulatorEvaluator:
    """Accumulate code block content in the document namespace.

    This evaluator stores parsed code block content in a list within the
    document's namespace. This is useful for testing parsers that group
    multiple code blocks together.

    The accumulated blocks are stored in the document namespace under a
    configurable key.
    """

    def __init__(self, namespace_key: str) -> None:
        """Initialize the block accumulator evaluator.

        Args:
            namespace_key: The key to use in the document namespace for
                storing accumulated blocks.
        """
        self._namespace_key = namespace_key

    def __call__(self, example: Example) -> None:
        """Add the parsed code block content to the namespace.

        Args:
            example: The example to evaluate.
        """
        existing_blocks = example.document.namespace.get(
            self._namespace_key,
            [],
        )
        example.document.namespace[self._namespace_key] = [
            *existing_blocks,
            example.parsed,
        ]
