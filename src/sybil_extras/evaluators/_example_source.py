"""Read parsed payloads from Sybil examples and regions."""

from typing import Protocol, TypeVar, runtime_checkable

_ParsedT_co = TypeVar("_ParsedT_co", covariant=True)


@runtime_checkable
class Parsed(Protocol[_ParsedT_co]):
    """Read-only view of the parser-specific payload Sybil exposes as
    Any.
    """

    @property
    def parsed(self) -> _ParsedT_co:
        """Get the payload produced by the parser."""
        ...


def parsed_value(*, example: Parsed[object]) -> object:
    """Read a payload whose type depends on the parser that produced
    it.
    """
    return example.parsed


def example_source(*, example: Parsed[object]) -> str:
    """Return the text of the parsed content."""
    return str(object=example.parsed)
