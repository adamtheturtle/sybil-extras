"""Tests for validation of values supplied by dependencies."""

from functools import partial
from subprocess import CalledProcessError

import pytest
from sybil import Region

from sybil_extras.languages import MARKDOWN
from tests._typing import failed_command, parsed_lexeme
from tests.conftest import (
    language_builder_id,
    language_builder_parameter,
    language_parameter,
)


def test_parsed_lexeme_rejects_plain_text() -> None:
    """Check that a plain string cannot supply source positions."""
    region = Region(start=0, end=4, parsed="pass")

    with pytest.raises(
        expected_exception=TypeError, match="Expected a Lexeme"
    ):
        _ = parsed_lexeme(example=region)


def test_failed_command_rejects_a_shell_string() -> None:
    """Check that the failed command was supplied as a list."""
    error = CalledProcessError(returncode=1, cmd="exit 1")

    with pytest.raises(
        expected_exception=TypeError,
        match="Expected the failed command to be an argument list",
    ):
        _ = failed_command(error=error)


def test_language_builder_id_requires_function() -> None:
    """A callable without a function name cannot supply a fixture ID."""
    builder = partial(MARKDOWN.directive_builders[0])

    with pytest.raises(
        expected_exception=TypeError,
        match="Expected a directive builder function",
    ):
        _ = language_builder_id(pair=(MARKDOWN, builder))


def test_language_parameter_rejects_string() -> None:
    """A language fixture parameter must be a markup language object."""
    with pytest.raises(
        expected_exception=TypeError,
        match="Unexpected markup language fixture parameter",
    ):
        _ = language_parameter(value="Markdown")


def test_language_builder_parameter_rejects_invalid_builder() -> None:
    """The language and builder fixture requires a callable builder."""
    with pytest.raises(
        expected_exception=TypeError,
        match="Unexpected language and directive builder fixture parameter",
    ):
        _ = language_builder_parameter(value=(MARKDOWN, "html_comment"))
