"""A parser for sphinx-jinja2 blocks in MyST using the myst-parser
library.
"""

import re
from collections.abc import Iterable

from beartype import beartype
from markdown_it.renderer import RendererHTML
from myst_parser.config.main import MdParserConfig
from myst_parser.parsers.mdit import create_md_parser
from sybil import Document, Region
from sybil.typing import Evaluator

from sybil_extras.parsers.myst_parser._line_offsets import line_offsets

_OPTION_PATTERN = re.compile(pattern=r"^:(?P<key>\w+):\s*(?P<value>.*)$")


@beartype
def _parse_options_and_body(
    content: str,
) -> tuple[dict[str, str], str]:
    """Separate options from body in directive content."""
    options: dict[str, str] = {}
    body_lines: list[str] = []
    in_options = True

    for line in content.split(sep="\n"):
        if in_options:
            option_match = _OPTION_PATTERN.match(string=line)
            if option_match:
                options[option_match.group("key")] = option_match.group(
                    "value"
                )
                continue
            if line.strip() == "":
                in_options = False
                continue
            in_options = False
        body_lines.append(line)

    body = "\n".join(body_lines)
    if body == "\n":
        body = ""

    return options, body


@beartype
class SphinxJinja2Parser:
    """A parser for sphinx-jinja2 blocks in MyST."""

    def __init__(
        self,
        *,
        evaluator: Evaluator,
    ) -> None:
        """
        Args:
            evaluator: The evaluator to use for evaluating the combined
        region.
        """
        self._evaluator = evaluator

    def __call__(self, document: Document) -> Iterable[Region]:
        """Parse the document for sphinx-jinja2 blocks."""
        config = MdParserConfig()
        md = create_md_parser(config=config, renderer=RendererHTML)
        md.disable(names="code")
        tokens = md.parse(src=document.text)
        offsets = line_offsets(text=document.text)

        for token in tokens:
            if token.type != "fence":
                continue

            # Only match {jinja} directives
            if token.info.strip() != "{jinja}":
                continue

            if token.map is None:  # pragma: no cover
                # This should never happen; map is always set for fence tokens.
                raise ValueError(token)

            start_line, end_line = token.map

            region_start = offsets[start_line]
            if end_line < len(offsets):
                next_line_start = offsets[end_line]
                region_end = next_line_start - 1
            else:
                region_end = len(document.text)

            options, body = _parse_options_and_body(
                content=token.content,
            )

            lexemes: dict[str, str | dict[str, str]] = {
                "directive": "jinja",
                "arguments": "",
                "source": body,
                "options": options,
            }

            region = Region(
                start=region_start,
                end=region_end,
                parsed=body,
                evaluator=self._evaluator,
                lexemes=lexemes,
            )
            yield region
