"""
Helpers shared across tests.
"""

from pathlib import Path

from sybil_extras.languages import MarkupLanguage


def join_markup(*parts: str) -> str:
    """
    Join markup fragments with blank lines, trimming edge newlines.
    """
    cleaned_parts = [part.strip("\n") for part in parts if part]
    return "\n\n".join(cleaned_parts)


def write_document(
    language: MarkupLanguage,
    directory: Path,
    content: str,
    *,
    stem: str = "test",
) -> Path:
    """
    Write ``content`` to ``directory`` using the language extension.
    """
    path = language.document_path(directory=directory, stem=stem)
    path.write_text(data=content, encoding="utf-8")
    return path
