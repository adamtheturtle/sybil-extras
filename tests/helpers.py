"""
Helpers shared across tests.
"""

from sybil_extras.languages import MarkupLanguage


def join_markup(language: MarkupLanguage, *parts: str) -> str:
    """
    Join markup fragments using the language's separator, trimming edge
    newlines.
    """
    return language.markup_separator.join(parts)
