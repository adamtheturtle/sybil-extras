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
    if not content:
        return ""
    normalized = content.rstrip("\n")
    # reStructuredText needs a blank line separating directives from
    # following content, so it keeps the double newline while other
    # languages only get a single trailing newline.
    suffix = "\n\n"
    return f"{normalized}{suffix}"
