"""Extract directive options and exact source using MyST's parser."""

from beartype import beartype
from myst_parser.parsers.directives import parse_directive_text


@beartype
def parse_directive(content: str) -> tuple[dict[str, str], str, int]:
    """Return options, exact body text and its offset in content lines."""
    result = parse_directive_text(
        directive_class=None,
        first_line="",
        content=content,
    )
    # MyST returns normalized body lines. Slice the original content so
    # executable source and writer replacements keep trailing whitespace.
    body = "".join(content.splitlines(keepends=True)[result.body_offset :])
    if not bool(body.strip()):
        body = ""
    return result.options, body, result.body_offset
