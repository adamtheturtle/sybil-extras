"""Shared pytest fixtures for tests package."""

import pytest

from sybil_extras.languages import (
    ALL_LANGUAGES,
    DirectiveBuilder,
    MarkupLanguage,
)

LANGUAGE_IDS = tuple(language.name for language in ALL_LANGUAGES)

LANGUAGE_DIRECTIVE_BUILDER_PARAMS = [
    (lang, builder)
    for lang in ALL_LANGUAGES
    for builder in lang.directive_builders
]

LANGUAGE_DIRECTIVE_BUILDER_IDS = [
    f"{lang.name}-directive-{index}"
    for lang in ALL_LANGUAGES
    for index, _ in enumerate(iterable=lang.directive_builders)
]


@pytest.fixture(name="language", params=ALL_LANGUAGES, ids=LANGUAGE_IDS)
def fixture_language(*, request: pytest.FixtureRequest) -> MarkupLanguage:
    """Provide each supported markup language."""
    language = request.param
    if not isinstance(language, MarkupLanguage):  # pragma: no cover
        message = "Unexpected markup language fixture parameter"
        raise TypeError(message)
    return language


@pytest.fixture(
    name="markup_language",
    params=ALL_LANGUAGES,
    ids=LANGUAGE_IDS,
)
def fixture_markup_language(
    *, request: pytest.FixtureRequest
) -> MarkupLanguage:
    """Provide each supported markup language."""
    language: object = request.param
    if not isinstance(language, MarkupLanguage):
        msg = "pytest supplied an unsupported markup language"
        raise TypeError(msg)
    return language


@pytest.fixture(
    name="language_directive_builder",
    params=LANGUAGE_DIRECTIVE_BUILDER_PARAMS,
    ids=LANGUAGE_DIRECTIVE_BUILDER_IDS,
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
    raw_param: object = request.param
    if not isinstance(raw_param, tuple):
        msg = "pytest supplied a non-tuple fixture parameter"
        raise TypeError(msg)
    if raw_param.__len__() != 2:  # noqa: PLR2004
        msg = "pytest supplied an invalid markup-language fixture parameter"
        raise TypeError(msg)
    if not isinstance(raw_param[0], MarkupLanguage) or not isinstance(
        raw_param[1],
        DirectiveBuilder,
    ):
        msg = "pytest supplied an invalid markup-language fixture parameter"
        raise TypeError(msg)
    return raw_param[0], raw_param[1]
