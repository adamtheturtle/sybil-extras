"""
Shared pytest fixtures for tests package.
"""

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
def fixture_language(request: pytest.FixtureRequest) -> MarkupLanguage:
    """
    Provide each supported markup language.
    """
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
def fixture_markup_language(request: pytest.FixtureRequest) -> MarkupLanguage:
    """
    Provide each supported markup language.
    """
    language: MarkupLanguage = request.param
    return language


@pytest.fixture(
    name="language_directive_builder",
    params=LANGUAGE_DIRECTIVE_BUILDER_PARAMS,
    ids=LANGUAGE_DIRECTIVE_BUILDER_IDS,
)
def fixture_language_directive_builder(
    request: pytest.FixtureRequest,
) -> tuple[MarkupLanguage, DirectiveBuilder]:
    """Provide each (language, directive_builder) combination.

    This allows testing all directive styles for languages that support
    multiple comment syntaxes (e.g., MyST with HTML and percent
    comments).
    """
    param: tuple[MarkupLanguage, DirectiveBuilder] = request.param
    return param
