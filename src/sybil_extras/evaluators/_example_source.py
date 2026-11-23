"""Extract text from parsed documentation examples."""

from typing import Protocol


class _ParsedExample(Protocol):
    """The parsed value exposed by an example."""

    @property
    def parsed(self) -> object:
        """Get the parsed result without assuming a specific type."""
        ...


def example_source(*, example: _ParsedExample) -> str:
    """Return the text of the parsed content."""
    return str(object=example.parsed)
