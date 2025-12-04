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


def document_data(language: MarkupLanguage, content: str) -> str:
    """
    Calculate the data ``write_document`` should persist.
    """
    if not content:
        return ""
    normalized = content.rstrip("\n")
    suffix = "\n\n" if language.file_extension == ".rst" else "\n"
    return f"{normalized}{suffix}"


def write_document(
    language: MarkupLanguage,
    directory: Path,
    data: str,
    *,
    stem: str = "test",
) -> Path:
    """
    Write ``data`` to ``directory`` using the language extension.
    """
    path = language.document_path(directory=directory, stem=stem)
    path.write_text(data=data, encoding="utf-8")
    return path
