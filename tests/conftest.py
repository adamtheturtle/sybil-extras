"""Shared pytest fixtures for tests package."""

import pytest

from sybil_extras.languages import (
    ALL_LANGUAGES,
    DirectiveBuilder,
    MarkupLanguage,
)


def _markup_language(*, value: MarkupLanguage) -> MarkupLanguage:
    """Type a markup language supplied by the pytest parameter API."""
    return value


def _language_builder_pair(
    *, value: tuple[MarkupLanguage, DirectiveBuilder]
) -> tuple[MarkupLanguage, DirectiveBuilder]:
    """Type a language and builder supplied by the pytest parameter
    API.
    """
    return value


@pytest.fixture(
    name="language", params=ALL_LANGUAGES, ids=lambda language: language.name
)
def fixture_language(*, request: pytest.FixtureRequest) -> MarkupLanguage:
    """Provide each supported markup language."""
    language = request.param
    # Pytest types request.param as Any; this check narrows it and rejects
    # unexpected parameters. See the upstream typing issue:
    # https://github.com/pytest-dev/pytest/issues/8763
    if not isinstance(language, MarkupLanguage):  # pragma: no cover
        message = "Unexpected markup language fixture parameter"
        raise TypeError(message)
    return language


@pytest.fixture(
    name="markup_language",
    params=ALL_LANGUAGES,
    ids=lambda language: language.name,
)
def fixture_markup_language(
    *, request: pytest.FixtureRequest
) -> MarkupLanguage:
    """Provide each supported markup language."""
    return _markup_language(value=request.param)


@pytest.fixture(
    name="language_directive_builder",
    params=[
        (lang, builder)
        for lang in ALL_LANGUAGES
        for builder in lang.directive_builders
    ],
    ids=lambda pair: f"{pair[0].name}-{pair[1].__name__.removeprefix('_')}",
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
    return _language_builder_pair(value=request.param)
