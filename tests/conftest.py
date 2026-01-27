"""Shared pytest fixtures for tests package."""

import uuid
from pathlib import Path

import pytest
from sybil.example import Example

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
def fixture_markup_language(request: pytest.FixtureRequest) -> MarkupLanguage:
    """Provide each supported markup language."""
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


def create_default_temp_file_path(
    *,
    example: Example,
    suffix: str = "",
) -> Path:
    """Create a temporary file path for an example code block.

    This is a test helper function that generates temporary file paths
    with informative names for debugging.

    The temporary file is created in the same directory as the source
    file and includes the source filename and line number in its name
    for easier identification in error messages.

    Args:
        example: The Sybil example for which to generate a filename.
        suffix: The suffix to use for the temporary file, e.g. ".py".

    Returns:
        A Path object for the temporary file.
    """
    path_name = Path(example.path).name
    # Replace characters that are not allowed in file names for Python
    # modules.
    sanitized_path_name = path_name.replace(".", "_").replace("-", "_")
    line_number_specifier = f"l{example.line}"
    prefix = f"{sanitized_path_name}_{line_number_specifier}_"

    # Create a sibling file in the same directory as the example file.
    # The name also looks like the example file name.
    # This is so that output reflects the actual file path.
    # This is useful for error messages, and for ignores.
    parent = Path(example.path).parent
    return parent / f"{prefix}{uuid.uuid4().hex[:4]}{suffix}"
