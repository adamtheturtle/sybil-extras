"""Shared pytest fixtures for tests package."""

from types import FunctionType

import pytest

from sybil_extras.languages import (
    ALL_LANGUAGES,
    DirectiveBuilder,
    MarkupLanguage,
)
from tests._typing import fixture_parameter


def _language_id(language: MarkupLanguage) -> str:
    """Use the markup language name as its pytest parameter ID."""
    return language.name


def language_builder_id(pair: tuple[MarkupLanguage, DirectiveBuilder]) -> str:
    """Use the markup language and builder names as the parameter ID."""
    language, builder = pair
    if not isinstance(builder, FunctionType):
        msg = "Expected a directive builder function"
        raise TypeError(msg)
    return f"{language.name}-{builder.__name__.removeprefix('_')}"


def language_parameter(*, value: object) -> MarkupLanguage:
    """Check that a fixture parameter is a supported markup language."""
    # Pytest types request.param as Any. See the upstream typing issue:
    # https://github.com/pytest-dev/pytest/issues/8763
    if not isinstance(value, MarkupLanguage):
        message = "Unexpected markup language fixture parameter"
        raise TypeError(message)
    return value


def language_builder_parameter(
    *, value: object
) -> tuple[MarkupLanguage, DirectiveBuilder]:
    """Check the language and builder fixture parameter."""
    match value:
        case (MarkupLanguage() as language, DirectiveBuilder() as builder):
            return language, builder
        case _:
            msg = "Unexpected language and directive builder fixture parameter"
            raise TypeError(msg)


@pytest.fixture(name="language", params=ALL_LANGUAGES, ids=_language_id)
def fixture_language(*, request: pytest.FixtureRequest) -> MarkupLanguage:
    """Provide each supported markup language."""
    return language_parameter(value=fixture_parameter(request=request))


@pytest.fixture(
    name="markup_language",
    params=ALL_LANGUAGES,
    ids=_language_id,
)
def fixture_markup_language(
    *, request: pytest.FixtureRequest
) -> MarkupLanguage:
    """Provide each supported markup language."""
    return language_parameter(value=fixture_parameter(request=request))


@pytest.fixture(
    name="language_directive_builder",
    params=[
        (lang, builder)
        for lang in ALL_LANGUAGES
        for builder in lang.directive_builders
    ],
    ids=language_builder_id,
)
def fixture_language_directive_builder(
    *,
    request: pytest.FixtureRequest,
) -> tuple[MarkupLanguage, DirectiveBuilder]:
    """Provide each (language, directive_builder) combination.

    This allows testing all directive styles for languages that support
    multiple comment syntaxes (e.g., MyST with HTML and percent
    comments).
    """
    return language_builder_parameter(value=fixture_parameter(request=request))
