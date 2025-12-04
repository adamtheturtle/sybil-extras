"""
Helpers shared across tests.
"""

from sybil_extras.languages import RESTRUCTUREDTEXT, MarkupLanguage


def join_markup(*parts: str) -> str:
    """
    Join markup fragments with blank lines, trimming edge newlines.
    """
    cleaned_parts = [part.strip("\n") for part in parts if part]
    return "\n\n".join(cleaned_parts)


def document_data(language: MarkupLanguage, content: str) -> str:
    """Calculate the normalized markup to persist.

    reStructuredText needs a blank line separating directives from
    following content, so it keeps the double newline while other
    languages only get a single trailing newline.
    """
    if not content:
        return ""
    normalized = content.rstrip("\n")
    suffix = "\n\n" if language is RESTRUCTUREDTEXT else "\n"
    return f"{normalized}{suffix}"
