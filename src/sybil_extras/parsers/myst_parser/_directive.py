"""Extract directive options and exact source using MyST's parser."""

from collections.abc import Callable

from beartype import beartype
from docutils.parsers.rst import Directive
from docutils.parsers.rst.directives import unchanged
from myst_parser.parsers.directives import parse_directive_text


class _OptionSpec(dict[str, Callable[[str], str]]):
    """Accept arbitrary options without interpreting their values."""

    def __bool__(self) -> bool:
        """Enable MyST's option parsing even before any keys exist."""
        return True

    def __missing__(self, key: str) -> Callable[[str], str]:
        """Preserve every option as a string, including empty flags."""
        return unchanged


class _SourceDirective(Directive):  # pylint: disable=abstract-method
    """Supply parsing metadata without instantiating or running a
    directive.
    """

    option_spec = _OptionSpec()
    has_content = True


@beartype
def parse_directive(content: str) -> tuple[dict[str, str], str, int]:
    """Return options, exact body text and its offset in content lines."""
    result = parse_directive_text(
        directive_class=_SourceDirective,
        first_line="",
        content=content,
    )
    # MyST returns normalized body lines. Slice the original content so
    # executable source and writer replacements keep trailing whitespace.
    body = "".join(content.splitlines(keepends=True)[result.body_offset :])
    if not bool(body.strip()):
        body = ""
    # MyST does not type the option keys and values; our converters above
    # guarantee that both are strings.
    options = dict[str, str](result.options)  # pyright: ignore[reportUnknownArgumentType, reportUnknownMemberType]
    return options, body, result.body_offset
