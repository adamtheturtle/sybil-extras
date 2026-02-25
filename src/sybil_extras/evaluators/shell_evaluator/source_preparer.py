"""Source preparers for shell command evaluators.

A source preparer extracts the raw source string from an example's parsed
content before it is written to a temporary file and passed to a shell
command.
"""

from typing import Protocol, runtime_checkable

from beartype import beartype
from sybil import Example


@beartype
@runtime_checkable
class SourcePreparer(Protocol):
    """Prepare source content from an example.

    Implementations extract the raw source string from an example's parsed
    content.  The returned string is then padded and written to a temporary
    file by the runner.
    """

    def __call__(
        self,
        *,
        example: Example,
    ) -> str:
        """Return the source string for the given example."""
        # We disable a pylint warning here because the ellipsis is required
        # for Pyright to recognize this as a protocol.
        ...  # pylint: disable=unnecessary-ellipsis


@beartype
class NoOpSourcePreparer:
    """Return the example's parsed content as-is."""

    def __call__(self, *, example: Example) -> str:
        """Return the parsed content of the example."""
        return str(object=example.parsed)


NOOP_SOURCE_PREPARER = NoOpSourcePreparer()
