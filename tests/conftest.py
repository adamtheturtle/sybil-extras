"""
Shared pytest fixtures for tests package.
"""

import pytest

from sybil_extras.languages import ALL_LANGUAGES, MarkupLanguage

LANGUAGE_IDS = tuple(language.name for language in ALL_LANGUAGES)


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
