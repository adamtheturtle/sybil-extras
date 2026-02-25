"""Result transformers for shell command evaluators.

A result transformer converts the formatted content (after padding has been
stripped) before it is written back to the document.
"""

from typing import Protocol, runtime_checkable

from beartype import beartype
from sybil import Example

from sybil_extras.evaluators._pycon import python_to_pycon


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


@beartype
class PyconResultTransformer:
    """Convert formatted Python back to pycon format.

    Adds ``>>>`` and ``...`` prompts and preserves output lines from the
    original pycon content when the statement structure is unchanged.
    """

    def __call__(self, *, content: str, example: Example) -> str:
        """Return the pycon-formatted version of the formatted Python."""
        return python_to_pycon(
            python_text=content,
            original_pycon=str(object=example.parsed),
        )
