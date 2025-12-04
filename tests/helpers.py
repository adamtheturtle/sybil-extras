"""
Helpers shared across tests.
"""

from sybil_extras.languages import MarkupLanguage


def join_markup(language: MarkupLanguage, *parts: str) -> str:
    """
    Join markup fragments using the language's separator, trimming edge
    newlines.
    """
    cleaned_parts = [part.strip("\n") for part in parts if part]
    return language.markup_separator.join(cleaned_parts)
