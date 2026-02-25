"""Result transformers for shell command evaluators.

A result transformer converts the formatted content (after padding has been
stripped) before it is written back to the document.
"""

from typing import Protocol, runtime_checkable

from beartype import beartype
from sybil import Example


@beartype
@runtime_checkable
class ResultTransformer(Protocol):
    """Transform the result content before it is written back.

    Implementations receive the formatted content (after padding has been
    stripped) and return the string that should replace the original code
    block in the document.
    """

    def __call__(
        self,
        *,
        content: str,
        example: Example,
    ) -> str:
        """Return the transformed content."""
        # We disable a pylint warning here because the ellipsis is required
        # for Pyright to recognize this as a protocol.
        ...  # pylint: disable=unnecessary-ellipsis


@beartype
class NoOpResultTransformer:
    """Return the content unchanged."""

    def __call__(self, *, content: str, example: Example) -> str:
        """Return the content as-is."""
        del example
        return content


NOOP_RESULT_TRANSFORMER = NoOpResultTransformer()
