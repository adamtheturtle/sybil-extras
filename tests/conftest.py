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


def _language_builder_id(pair: tuple[MarkupLanguage, DirectiveBuilder]) -> str:
    """Use the markup language and builder names as the parameter ID."""
    language, builder = pair
    if not isinstance(builder, FunctionType):  # pragma: no cover
        msg = "Expected a directive builder function"
        raise TypeError(msg)
    return f"{language.name}-{builder.__name__.removeprefix('_')}"


def _requested_language(*, request: pytest.FixtureRequest) -> MarkupLanguage:
    """Provide each supported markup language."""
    language = fixture_parameter(request=request)
    # Pytest types request.param as Any; this check narrows it and rejects
    # unexpected parameters. See the upstream typing issue:
    # https://github.com/pytest-dev/pytest/issues/8763
    if not isinstance(language, MarkupLanguage):  # pragma: no cover
        message = "Unexpected markup language fixture parameter"
        raise TypeError(message)
    return language


@pytest.fixture(name="language", params=ALL_LANGUAGES, ids=_language_id)
def fixture_language(*, request: pytest.FixtureRequest) -> MarkupLanguage:
    """Provide each supported markup language."""
    return _requested_language(request=request)


@pytest.fixture(
    name="markup_language",
    params=ALL_LANGUAGES,
    ids=_language_id,
)
def fixture_markup_language(
    *, request: pytest.FixtureRequest
) -> MarkupLanguage:
    """Provide each supported markup language."""
    return _requested_language(request=request)


@pytest.fixture(
    name="language_directive_builder",
    params=[
        (lang, builder)
        for lang in ALL_LANGUAGES
        for builder in lang.directive_builders
    ],
    ids=_language_builder_id,
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
    match fixture_parameter(request=request):
        case (MarkupLanguage() as language, DirectiveBuilder() as builder):
            return language, builder
        case _:  # pragma: no cover
            msg = "Unexpected language and directive builder fixture parameter"
            raise TypeError(msg)
