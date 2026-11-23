"""Typed access to values supplied by dependencies."""

from typing import (
    TYPE_CHECKING,
    Protocol,
    TypeGuard,
    TypeVar,
    runtime_checkable,
)

from sybil import Lexeme, Region

from sybil_extras.evaluators._example_source import Parsed, parsed_value

if TYPE_CHECKING:
    from collections.abc import Mapping


_ParameterT_co = TypeVar("_ParameterT_co", covariant=True)


@runtime_checkable
class FixtureParameter(Protocol[_ParameterT_co]):
    """A parametrized fixture request."""

    @property
    def param(self) -> _ParameterT_co:
        """The value supplied by the fixture declaration."""
        ...


def _require_lexeme(*, value: object) -> Lexeme:
    """Check the parser or lexer contract before reading a lexeme."""
    assert isinstance(value, Lexeme)
    return value


def parsed_lexeme(*, example: Parsed[object]) -> Lexeme:
    """Read a lexeme from a parsed payload."""
    return _require_lexeme(value=parsed_value(example=example))


def source_lexeme(*, region: Region) -> Lexeme:
    """Read the source lexeme from a lexer region."""
    lexemes: Mapping[str, object] = region.lexemes
    return _require_lexeme(value=lexemes["source"])


def is_object_list(value: object, /) -> TypeGuard[list[object]]:
    """Check that a value is a list before inspecting its items."""
    return isinstance(value, list)


class _CommandError(Protocol):
    """A process error exposing the failed command."""

    @property
    def cmd(self) -> object:
        """Get the command that failed."""
        ...


def failed_command(*, error: _CommandError) -> object:
    """Read the command from a process error."""
    return error.cmd
