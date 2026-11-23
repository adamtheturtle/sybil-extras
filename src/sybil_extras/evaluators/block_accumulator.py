"""Block accumulator evaluator."""

import threading
from collections.abc import Iterable, Mapping
from typing import TypeGuard

from beartype import beartype
from sybil.example import Example

from sybil_extras.evaluators._example_source import parsed_value


def _is_iterable(value: object, /) -> TypeGuard[Iterable[object]]:
    """Check whether a namespace value can supply accumulated blocks."""
    return isinstance(value, Iterable)


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
        self._lock = threading.Lock()

    def __call__(self, example: Example) -> None:
        """Add the parsed code block content to the namespace.

        Args:
            example: The example to evaluate.
        """
        with self._lock:
            namespace: Mapping[str, object] = example.document.namespace
            existing_blocks = namespace.get(self._namespace_key, ())
            if _is_iterable(existing_blocks):
                example.document.namespace[self._namespace_key] = [
                    *existing_blocks,
                    parsed_value(example=example),
                ]
            else:
                msg = "Accumulated blocks must be iterable"
                raise TypeError(msg)
