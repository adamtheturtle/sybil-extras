"""
Helpers and fixtures for testing parsers across markup languages.
"""

from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path

from sybil import Document, Sybil
from sybil.parsers.markdown.codeblock import (
    CodeBlockParser as MarkdownCodeBlockParser,
)
from sybil.parsers.markdown.codeblock import (
    PythonCodeBlockParser as MarkdownPythonCodeBlockParser,
)
from sybil.parsers.markdown.skip import SkipParser as MarkdownSkipParser
from sybil.parsers.myst.codeblock import (
    CodeBlockParser as MystCodeBlockParser,
)
from sybil.parsers.myst.codeblock import (
    PythonCodeBlockParser as MystPythonCodeBlockParser,
)
from sybil.parsers.myst.skip import SkipParser as MystSkipParser
from sybil.parsers.rest.codeblock import (
    CodeBlockParser as ReSTCodeBlockParser,
)
from sybil.parsers.rest.codeblock import (
    PythonCodeBlockParser as ReSTPythonCodeBlockParser,
)
from sybil.parsers.rest.skip import SkipParser as ReSTSkipParser
from sybil.region import Region

from sybil_extras.parsers.markdown.custom_directive_skip import (
    CustomDirectiveSkipParser as MarkdownCustomSkipParser,
)
from sybil_extras.parsers.markdown.group_all import (
    GroupAllParser as MarkdownGroupAllParser,
)
from sybil_extras.parsers.markdown.grouped_source import (
    GroupedSourceParser as MarkdownGroupedSourceParser,
)
from sybil_extras.parsers.myst.custom_directive_skip import (
    CustomDirectiveSkipParser as MystCustomSkipParser,
)
from sybil_extras.parsers.myst.group_all import (
    GroupAllParser as MystGroupAllParser,
)
from sybil_extras.parsers.myst.grouped_source import (
    GroupedSourceParser as MystGroupedSourceParser,
)
from sybil_extras.parsers.myst.sphinx_jinja2 import (
    SphinxJinja2Parser as MystSphinxJinja2Parser,
)
from sybil_extras.parsers.rest.custom_directive_skip import (
    CustomDirectiveSkipParser as ReSTCustomSkipParser,
)
from sybil_extras.parsers.rest.group_all import (
    GroupAllParser as ReSTGroupAllParser,
)
from sybil_extras.parsers.rest.grouped_source import (
    GroupedSourceParser as ReSTGroupedSourceParser,
)
from sybil_extras.parsers.rest.sphinx_jinja2 import (
    SphinxJinja2Parser as ReSTSphinxJinja2Parser,
)


def _rst_code_block(body: str) -> str:
    """
    Render a Python code block in reStructuredText.
    """

    def _indent(line: str) -> str:
        """
        Indent a line for inclusion in a code block.
        """
        return f"    {line}" if line else ""

    indented_body = "\n".join(_indent(line=line) for line in body.splitlines())
    return f".. code-block:: python\n\n{indented_body}"


def _markdown_code_block(body: str) -> str:
    """
    Render a fenced Python code block.
    """
    return f"```python\n{body}\n```"


def _rst_directive(text: str) -> str:
    """
    Render a directive for reStructuredText.
    """
    return f".. {text}"


def _html_directive(text: str) -> str:
    """
    Render directive-like comments for Markdown-based formats.
    """
    return f"<!--- {text} -->"


def _myst_percent_directive(text: str) -> str:
    """
    Render MyST percent-style directives.
    """
    return f"% {text}"


class _UnsupportedSphinxJinja2Parser:
    """
    Placeholder parser for markups without sphinx-jinja2 support.
    """

    def __init__(self, *args: object) -> None: ...


@dataclass(frozen=True)
class MarkupLanguage:
    """
    Information required to generate documents for a markup language.
    """

    name: str
    extension: str
    code_block_parser_cls: type
    python_code_block_parser_cls: type
    skip_parser_cls: type
    group_all_parser_cls: type
    grouped_source_parser_cls: type
    _block_renderer: Callable[[str], str]
    _directive_renderer: Callable[[str], str]
    custom_skip_parser_cls: type
    sphinx_jinja_parser_cls: type
    trailing_newline: bool = False

    def code_block(self, body: str) -> str:
        """
        Create a code block fragment.
        """
        return self._block_renderer(body.rstrip("\n"))

    def directive(self, directive: str) -> str:
        """
        Create a directive fragment.
        """
        return self._directive_renderer(directive)

    def document(self, *parts: str) -> str:
        """
        Combine fragments into a document body.
        """
        cleaned_parts = [
            part.strip("\n") for part in parts if part.strip("\n")
        ]
        return "\n\n".join(cleaned_parts) + "\n"

    def expected_text(self, text: str) -> str:
        """
        Adjust an expected string for markup quirks.
        """
        if text.endswith("\n") or not self.trailing_newline:
            return text
        return f"{text}\n"


MARKUP_LANGUAGES: tuple[MarkupLanguage, ...] = (
    MarkupLanguage(
        name="reStructuredText",
        extension="rst",
        code_block_parser_cls=ReSTCodeBlockParser,
        python_code_block_parser_cls=ReSTPythonCodeBlockParser,
        skip_parser_cls=ReSTSkipParser,
        group_all_parser_cls=ReSTGroupAllParser,
        grouped_source_parser_cls=ReSTGroupedSourceParser,
        custom_skip_parser_cls=ReSTCustomSkipParser,
        sphinx_jinja_parser_cls=ReSTSphinxJinja2Parser,
        trailing_newline=False,
        _block_renderer=_rst_code_block,
        _directive_renderer=_rst_directive,
    ),
    MarkupLanguage(
        name="Markdown",
        extension="md",
        code_block_parser_cls=MarkdownCodeBlockParser,
        python_code_block_parser_cls=MarkdownPythonCodeBlockParser,
        skip_parser_cls=MarkdownSkipParser,
        group_all_parser_cls=MarkdownGroupAllParser,
        grouped_source_parser_cls=MarkdownGroupedSourceParser,
        custom_skip_parser_cls=MarkdownCustomSkipParser,
        sphinx_jinja_parser_cls=_UnsupportedSphinxJinja2Parser,
        trailing_newline=True,
        _block_renderer=_markdown_code_block,
        _directive_renderer=_html_directive,
    ),
    MarkupLanguage(
        name="MyST",
        extension="md",
        code_block_parser_cls=MystCodeBlockParser,
        python_code_block_parser_cls=MystPythonCodeBlockParser,
        skip_parser_cls=MystSkipParser,
        group_all_parser_cls=MystGroupAllParser,
        grouped_source_parser_cls=MystGroupedSourceParser,
        custom_skip_parser_cls=MystCustomSkipParser,
        sphinx_jinja_parser_cls=MystSphinxJinja2Parser,
        trailing_newline=True,
        _block_renderer=_markdown_code_block,
        _directive_renderer=_html_directive,
    ),
    MarkupLanguage(
        name="MyST (percent directives)",
        extension="md",
        code_block_parser_cls=MystCodeBlockParser,
        python_code_block_parser_cls=MystPythonCodeBlockParser,
        skip_parser_cls=MystSkipParser,
        group_all_parser_cls=MystGroupAllParser,
        grouped_source_parser_cls=MystGroupedSourceParser,
        custom_skip_parser_cls=MystCustomSkipParser,
        sphinx_jinja_parser_cls=MystSphinxJinja2Parser,
        trailing_newline=True,
        _block_renderer=_markdown_code_block,
        _directive_renderer=_myst_percent_directive,
    ),
)


def parse_document(
    *,
    tmp_path: Path,
    markup: MarkupLanguage,
    parts: Sequence[str],
    parsers: Sequence[Callable[[Document], Iterable[Region]]],
) -> Document:
    """
    Parse the provided fragments as a document for the given markup.
    """
    document_path = tmp_path / f"test_document.{markup.extension}"
    document_path.write_text(data=markup.document(*parts), encoding="utf-8")

    sybil = Sybil(parsers=list(parsers))
    return sybil.parse(path=document_path)


def evaluate_document(
    *,
    tmp_path: Path,
    markup: MarkupLanguage,
    parts: Sequence[str],
    parsers: Sequence[Callable[[Document], Iterable[Region]]],
) -> Document:
    """
    Parse and evaluate all examples in the generated document.
    """
    document = parse_document(
        tmp_path=tmp_path,
        markup=markup,
        parts=parts,
        parsers=parsers,
    )
    for example in document.examples():
        example.evaluate()
    return document
