"""
Shared pytest fixtures for tests package.
"""

import pytest

from sybil_extras.languages import (
    ALL_LANGUAGES,
    DirectiveStyle,
    MarkupLanguage,
)

LANGUAGE_IDS = tuple(language.name for language in ALL_LANGUAGES)

LANGUAGE_DIRECTIVE_STYLE_PARAMS = [
    (lang, style) for lang in ALL_LANGUAGES for style in lang.directive_styles
]

LANGUAGE_DIRECTIVE_STYLE_IDS = [
    f"{lang.name}-directive-{i}"
    for lang in ALL_LANGUAGES
    for i, _ in enumerate(lang.directive_styles)
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
    language = request.param
    if not isinstance(language, MarkupLanguage):  # pragma: no cover
        message = "Unexpected markup language fixture parameter"
        raise TypeError(message)
    return language


@pytest.fixture(
    name="language_directive_style",
    params=LANGUAGE_DIRECTIVE_STYLE_PARAMS,
    ids=LANGUAGE_DIRECTIVE_STYLE_IDS,
)
def fixture_language_directive_style(
    request: pytest.FixtureRequest,
) -> tuple[MarkupLanguage, DirectiveStyle]:
    """Provide each (language, directive_style) combination.

    This allows testing all directive styles for languages that support
    multiple comment syntaxes (e.g., MyST with HTML and percent
    comments).
    """
    param = request.param
    if not isinstance(param, tuple):  # pragma: no cover
        message = "Unexpected fixture parameter type"
        raise TypeError(message)
    return param
