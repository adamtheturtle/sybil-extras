"""Extract directive options and exact source using MyST's option
parser.
"""

from textwrap import dedent

from beartype import beartype
from myst_parser.parsers.directives import is_option_line
from myst_parser.parsers.options import options_to_items


@beartype
def parse_directive(content: str) -> tuple[dict[str, str], str, int]:
    """Return options, exact body text and its offset in content lines."""
    lines = content.splitlines(keepends=True)
    body_offset = 0
    option_lines: list[str] = []
    if content.startswith("---"):
        body_offset = 1
        while body_offset < len(lines) and not lines[body_offset].startswith(
            "---"
        ):
            option_lines.append(lines[body_offset].rstrip("\r\n"))
            body_offset += 1
        body_offset = min(body_offset + 1, len(lines))
    else:
        while body_offset < len(lines) and is_option_line(
            line=lines[body_offset]
        ):
            option_lines.append(lines[body_offset].lstrip()[1:].rstrip("\r\n"))
            body_offset += 1

    options, _ = options_to_items(text=dedent(text="\n".join(option_lines)))
    if body_offset < len(lines) and not bool(lines[body_offset].strip()):
        body_offset += 1
    body = "".join(lines[body_offset:])
    if not bool(body.strip()):
        body = ""
    return dict(options), body, body_offset
