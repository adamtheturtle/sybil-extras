"""Typed access to values supplied by dependencies."""

from typing import TYPE_CHECKING, Protocol, TypeGuard

from sybil import Lexeme, Region

from sybil_extras.evaluators._example_source import Parsed, parsed_value

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence


class _FixtureParameter(Protocol):
    """A parametrized fixture request."""

    @property
    def param(self) -> object:
        """The value supplied by the fixture declaration."""
        ...


def fixture_parameter(*, request: _FixtureParameter) -> object:
    """Read a pytest fixture parameter without assuming its type."""
    return request.param


def _require_lexeme(*, value: object) -> Lexeme:
    """Check the parser or lexer contract before reading a lexeme."""
    if not isinstance(value, Lexeme):
        msg = "Expected a Lexeme"
        raise TypeError(msg)
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


def failed_command(*, error: _CommandError) -> "Sequence[object]":
    """Check that the failed command was passed as an argument list."""
    command = error.cmd
    if not is_object_list(command):
        msg = "Expected the failed command to be an argument list"
        raise TypeError(msg)
    return command
