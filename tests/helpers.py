"""
Helpers shared across tests.
"""


def join_markup(*parts: str) -> str:
    """
    Join markup fragments with blank lines, trimming edge newlines.
    """
    cleaned_parts = [part.strip("\n") for part in parts if part]
    return "\n\n".join(cleaned_parts)


def document_data(content: str) -> str:
    """Calculate the normalized markup to persist.

    Always keep a blank line separating directives from content across
    languages. This intentionally differs from
    :func:`sybil_extras.languages._normalize_code`, which dedents block
    content and would corrupt the indentation required in the serialized
    markup.
    """
    normalized = content.rstrip("\n")
    return f"{normalized}\n\n"
