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

from sybil_extras.parsers._line_offsets import line_offsets
from sybil_extras.parsers.myst_parser._directive import parse_directive

_JINJA_INFO_PATTERN = re.compile(
    pattern=r"^\{jinja\}(?:\s+(?P<arguments>.*))?$"
)


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
        _ = md.disable(names="code")
        tokens = md.parse(src=document.text)
        offsets = line_offsets(text=document.text)

        for token in tokens:
            if token.type != "fence":
                continue

            # Only match {jinja} directives, with an optional argument.
            info_match = _JINJA_INFO_PATTERN.fullmatch(
                string=token.info.strip()
            )
            if info_match is None:
                continue
            arguments = info_match.group("arguments")
            if arguments is None:
                arguments = ""

            # The built-in fence rule sets map. Upstream proposes a token
            # class with a required map:
            # https://github.com/executablebooks/markdown-it-py/pull/431
            if token.map is None:  # pragma: no cover
                raise ValueError(token)

            start_line, end_line = token.map

            region_start = offsets[start_line]
            if end_line < len(offsets):
                next_line_start = offsets[end_line]
                region_end = next_line_start - 1
            else:
                region_end = len(document.text)

            options, body, _ = parse_directive(
                content=token.content,
            )

            lexemes: dict[str, str | dict[str, str]] = {
                "directive": "jinja",
                "arguments": arguments,
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
