"""Shared pytest fixtures for tests package."""

from types import FunctionType

import pytest

from sybil_extras.languages import (
    ALL_LANGUAGES,
    DirectiveBuilder,
    MarkupLanguage,
)
from tests._typing import FixtureParameter


def _language_id(language: MarkupLanguage) -> str:
    """Use the markup language name as its pytest parameter ID."""
    return language.name


def _language_builder_id(pair: tuple[MarkupLanguage, DirectiveBuilder]) -> str:
    """Use the markup language and builder names as the parameter ID."""
    language, builder = pair
    assert isinstance(builder, FunctionType)
    return f"{language.name}-{builder.__name__.removeprefix('_')}"


@pytest.fixture(name="language", params=ALL_LANGUAGES, ids=_language_id)
def fixture_language(
    *, request: FixtureParameter[MarkupLanguage]
) -> MarkupLanguage:
    """Provide each supported markup language."""
    return request.param


@pytest.fixture(
    name="markup_language",
    params=ALL_LANGUAGES,
    ids=_language_id,
)
def fixture_markup_language(
    *, request: FixtureParameter[MarkupLanguage]
) -> MarkupLanguage:
    """Provide each supported markup language."""
    return request.param


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
    request: FixtureParameter[tuple[MarkupLanguage, DirectiveBuilder]],
) -> tuple[MarkupLanguage, DirectiveBuilder]:
    """Provide each (language, directive_builder) combination.

    This allows testing all directive styles for languages that support
    multiple comment syntaxes (e.g., MyST with HTML and percent
    comments).
    """
    return request.param
