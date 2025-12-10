"""
Tools for managing markup languages and generating snippets.
"""

import textwrap
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

import sybil.parsers.markdown
import sybil.parsers.myst
import sybil.parsers.rest
from beartype import beartype
from sybil import Document, Region
from sybil.evaluators.skip import Skipper
from sybil.typing import Evaluator

import sybil_extras.parsers.djot.codeblock
import sybil_extras.parsers.djot.custom_directive_skip
import sybil_extras.parsers.djot.group_all
import sybil_extras.parsers.djot.grouped_source
import sybil_extras.parsers.markdown.custom_directive_skip
import sybil_extras.parsers.markdown.group_all
import sybil_extras.parsers.markdown.grouped_source
import sybil_extras.parsers.mdx.codeblock
import sybil_extras.parsers.mdx.custom_directive_skip
import sybil_extras.parsers.mdx.group_all
import sybil_extras.parsers.mdx.grouped_source
import sybil_extras.parsers.myst.custom_directive_skip
import sybil_extras.parsers.myst.group_all
import sybil_extras.parsers.myst.grouped_source
import sybil_extras.parsers.myst.sphinx_jinja2
import sybil_extras.parsers.norg.codeblock
import sybil_extras.parsers.norg.custom_directive_skip
import sybil_extras.parsers.norg.group_all
import sybil_extras.parsers.norg.grouped_source
import sybil_extras.parsers.rest.custom_directive_skip
import sybil_extras.parsers.rest.group_all
import sybil_extras.parsers.rest.grouped_source
import sybil_extras.parsers.rest.sphinx_jinja2


@runtime_checkable
class _SphinxJinja2Parser(Protocol):
    """
    A parser for sphinx-jinja2 blocks.
    """

    def __init__(self, *, evaluator: Evaluator) -> None:
        """
        Construct a sphinx-jinja2 parser.
        """
        # We disable a pylint warning here because the ellipsis is required
        # for pyright to recognize this as a protocol.
        ...  # pylint: disable=unnecessary-ellipsis

    def __call__(self, document: Document) -> Iterable[Region]:
        """
        Call the sphinx-jinja2 parser.
        """
        # We disable a pylint warning here because the ellipsis is required
        # for pyright to recognize this as a protocol.
        ...  # pylint: disable=unnecessary-ellipsis


@runtime_checkable
class _SkipParser(Protocol):
    """
    A parser for skipping custom directives.
    """

    def __init__(self, directive: str) -> None:
        """
        Construct a skip parser.
        """
        # We disable a pylint warning here because the ellipsis is required
        # for pyright to recognize this as a protocol.
        ...  # pylint: disable=unnecessary-ellipsis

    def __call__(self, document: Document) -> Iterable[Region]:
        """
        Call the skip parser.
        """
        # We disable a pylint warning here because the ellipsis is required
        # for pyright to recognize this as a protocol.
        ...  # pylint: disable=unnecessary-ellipsis

    def get_skipper(self) -> Skipper:
        """
        Return the skipper managing skip state.
        """
        ...  # pylint: disable=unnecessary-ellipsis


@runtime_checkable
class _GroupedSourceParser(Protocol):
    """
    A parser for grouping code blocks.
    """

    def __init__(
        self,
        *,
        directive: str,
        evaluator: Evaluator,
        pad_groups: bool,
    ) -> None:
        """
        Construct a grouped code block parser.
        """
        # We disable a pylint warning here because the ellipsis is required
        # for pyright to recognize this as a protocol.
        ...  # pylint: disable=unnecessary-ellipsis

    def __call__(self, document: Document) -> Iterable[Region]:
        """
        Call the grouped code block parser.
        """
        # We disable a pylint warning here because the ellipsis is required
        # for pyright to recognize this as a protocol.
        ...  # pylint: disable=unnecessary-ellipsis


@runtime_checkable
class _GroupAllParser(Protocol):
    """
    A parser for grouping all code blocks in a document.
    """

    def __init__(
        self,
        *,
        evaluator: Evaluator,
        pad_groups: bool,
    ) -> None:
        """
        Construct a parser that groups every code block.
        """
        ...  # pylint: disable=unnecessary-ellipsis

    def __call__(self, document: Document) -> Iterable[Region]:
        """
        Call the group-all parser.
        """
        ...  # pylint: disable=unnecessary-ellipsis


@runtime_checkable
class CodeBlockBuilder(Protocol):
    """
    A callable that renders code blocks for a markup language.
    """

    def __call__(self, code: str, language: str) -> str:
        """
        Render ``code`` for ``language``.
        """
        ...  # pylint: disable=unnecessary-ellipsis


@runtime_checkable
class DirectiveBuilder(Protocol):
    """
    A callable that renders directives for a markup language.
    """

    def __call__(self, directive: str, argument: str | None = None) -> str:
        """
        Render ``directive`` with the optional ``argument``.
        """
        ...  # pylint: disable=unnecessary-ellipsis


@runtime_checkable
class JinjaBlockBuilder(Protocol):
    """
    A callable that renders Jinja blocks for a markup language.
    """

    def __call__(self, body: str) -> str:
        """
        Render a Jinja block containing ``body``.
        """
        ...  # pylint: disable=unnecessary-ellipsis


@beartype
def _normalize_code(content: str) -> str:
    """
    Normalize code provided in tests into a block-friendly form.
    """
    normalized = textwrap.dedent(text=content).strip("\n")
    if not normalized:
        return ""
    return f"{normalized}\n"


@beartype
def _markdown_code_block(code: str, language: str) -> str:
    """
    Build a Markdown/MyST code block.
    """
    normalized = _normalize_code(content=code)
    return f"```{language}\n{normalized}```"


@beartype
def _rst_code_block(code: str, language: str) -> str:
    """
    Build a reStructuredText code block.
    """
    normalized = _normalize_code(content=code)
    indented = (
        textwrap.indent(text=normalized, prefix="   ") if normalized else ""
    )
    return f".. code-block:: {language}\n\n{indented}".rstrip()


@beartype
def _html_comment_directive(
    directive: str,
    argument: str | None = None,
) -> str:
    """
    Render a directive embedded in an HTML comment.
    """
    suffix = f": {argument}" if argument is not None else ""
    return f"<!--- {directive}{suffix} -->"


@beartype
def _percent_comment_directive(
    directive: str,
    argument: str | None = None,
) -> str:
    """
    Render a directive embedded in a percent-style comment.
    """
    suffix = f": {argument}" if argument is not None else ""
    return f"% {directive}{suffix}"


@beartype
def _rst_directive(
    directive: str,
    argument: str | None = None,
) -> str:
    """
    Render a directive for reStructuredText documents.
    """
    if argument is None:
        return f".. {directive}:"
    return f".. {directive}: {argument}"


@beartype
def _djot_directive(
    directive: str,
    argument: str | None = None,
) -> str:
    """
    Render a directive embedded in a djot comment.
    """
    suffix = f": {argument}" if argument is not None else ""
    return f"{{% {directive}{suffix} %}}"


@beartype
def _norg_code_block(code: str, language: str) -> str:
    """
    Build a Norg verbatim ranged tag code block.
    """
    normalized = _normalize_code(content=code)
    lang_param = f" {language}" if language else ""
    return f"@code{lang_param}\n{normalized}@end"


@beartype
def _norg_directive(
    directive: str,
    argument: str | None = None,
) -> str:
    """
    Render a directive embedded in a norg infirm tag.
    """
    suffix = f": {argument}" if argument is not None else ""
    return f".{directive}{suffix}"


@beartype
def _myst_jinja_block(body: str) -> str:
    """
    Render a sphinx-jinja block for MyST.
    """
    normalized = _normalize_code(content=body)
    return f"```{{jinja}}\n{normalized}```"


@beartype
def _rst_jinja_block(body: str) -> str:
    """
    Render a sphinx-jinja block for reStructuredText.
    """
    normalized = _normalize_code(content=body)
    indented = (
        textwrap.indent(text=normalized, prefix="   ") if normalized else ""
    )
    return f".. jinja::\n\n{indented}".rstrip()


@runtime_checkable
class _CodeBlockParser(Protocol):
    """
    A parser for code blocks.
    """

    def __init__(
        self,
        *,
        language: str | None = None,
        evaluator: Evaluator | None = None,
    ) -> None:
        """
        Construct a code block parser.
        """
        # We disable a pylint warning here because the ellipsis is required
        # for pyright to recognize this as a protocol.
        ...  # pylint: disable=unnecessary-ellipsis

    def __call__(self, document: Document) -> Iterable[Region]:
        """
        Call the code block parser.
        """
        # We disable a pylint warning here because the ellipsis is required
        # for pyright to recognize this as a protocol.
        ...  # pylint: disable=unnecessary-ellipsis


@beartype
@dataclass(frozen=True)
class MarkupLanguage:
    """
    A markup language.
    """

    name: str
    markup_separator: str
    skip_parser_cls: type[_SkipParser]
    code_block_parser_cls: type[_CodeBlockParser]
    group_parser_cls: type[_GroupedSourceParser]
    group_all_parser_cls: type[_GroupAllParser]
    sphinx_jinja_parser_cls: type[_SphinxJinja2Parser] | None
    code_block_builder: CodeBlockBuilder
    directive_builder: DirectiveBuilder
    jinja_block_builder: JinjaBlockBuilder | None


MYST = MarkupLanguage(
    name="MyST",
    markup_separator="\n",
    skip_parser_cls=(
        sybil_extras.parsers.myst.custom_directive_skip.CustomDirectiveSkipParser
    ),
    code_block_parser_cls=sybil.parsers.myst.CodeBlockParser,
    group_parser_cls=sybil_extras.parsers.myst.grouped_source.GroupedSourceParser,
    group_all_parser_cls=sybil_extras.parsers.myst.group_all.GroupAllParser,
    sphinx_jinja_parser_cls=sybil_extras.parsers.myst.sphinx_jinja2.SphinxJinja2Parser,
    code_block_builder=_markdown_code_block,
    directive_builder=_html_comment_directive,
    jinja_block_builder=_myst_jinja_block,
)

MYST_PERCENT_COMMENTS = MarkupLanguage(
    name="MyST (percent comments)",
    markup_separator="\n\n",
    skip_parser_cls=(
        sybil_extras.parsers.myst.custom_directive_skip.CustomDirectiveSkipParser
    ),
    code_block_parser_cls=sybil.parsers.myst.CodeBlockParser,
    group_parser_cls=sybil_extras.parsers.myst.grouped_source.GroupedSourceParser,
    group_all_parser_cls=sybil_extras.parsers.myst.group_all.GroupAllParser,
    sphinx_jinja_parser_cls=sybil_extras.parsers.myst.sphinx_jinja2.SphinxJinja2Parser,
    code_block_builder=_markdown_code_block,
    directive_builder=_percent_comment_directive,
    jinja_block_builder=_myst_jinja_block,
)

RESTRUCTUREDTEXT = MarkupLanguage(
    name="reStructuredText",
    markup_separator="\n\n",
    skip_parser_cls=sybil_extras.parsers.rest.custom_directive_skip.CustomDirectiveSkipParser,
    code_block_parser_cls=sybil.parsers.rest.CodeBlockParser,
    group_parser_cls=sybil_extras.parsers.rest.grouped_source.GroupedSourceParser,
    group_all_parser_cls=sybil_extras.parsers.rest.group_all.GroupAllParser,
    sphinx_jinja_parser_cls=sybil_extras.parsers.rest.sphinx_jinja2.SphinxJinja2Parser,
    code_block_builder=_rst_code_block,
    directive_builder=_rst_directive,
    jinja_block_builder=_rst_jinja_block,
)

MARKDOWN = MarkupLanguage(
    name="Markdown",
    markup_separator="\n",
    skip_parser_cls=sybil_extras.parsers.markdown.custom_directive_skip.CustomDirectiveSkipParser,
    code_block_parser_cls=sybil.parsers.markdown.CodeBlockParser,
    group_parser_cls=sybil_extras.parsers.markdown.grouped_source.GroupedSourceParser,
    group_all_parser_cls=sybil_extras.parsers.markdown.group_all.GroupAllParser,
    sphinx_jinja_parser_cls=None,
    code_block_builder=_markdown_code_block,
    directive_builder=_html_comment_directive,
    jinja_block_builder=None,
)

MDX = MarkupLanguage(
    name="MDX",
    markup_separator="\n",
    skip_parser_cls=sybil_extras.parsers.mdx.custom_directive_skip.CustomDirectiveSkipParser,
    code_block_parser_cls=sybil_extras.parsers.mdx.codeblock.CodeBlockParser,
    group_parser_cls=sybil_extras.parsers.mdx.grouped_source.GroupedSourceParser,
    group_all_parser_cls=sybil_extras.parsers.mdx.group_all.GroupAllParser,
    sphinx_jinja_parser_cls=None,
    code_block_builder=_markdown_code_block,
    directive_builder=_html_comment_directive,
    jinja_block_builder=None,
)

DJOT = MarkupLanguage(
    name="Djot",
    markup_separator="\n",
    skip_parser_cls=sybil_extras.parsers.djot.custom_directive_skip.CustomDirectiveSkipParser,
    code_block_parser_cls=sybil_extras.parsers.djot.codeblock.CodeBlockParser,
    group_parser_cls=sybil_extras.parsers.djot.grouped_source.GroupedSourceParser,
    group_all_parser_cls=sybil_extras.parsers.djot.group_all.GroupAllParser,
    sphinx_jinja_parser_cls=None,
    code_block_builder=_markdown_code_block,
    directive_builder=_djot_directive,
    jinja_block_builder=None,
)

NORG = MarkupLanguage(
    name="Norg",
    markup_separator="\n",
    skip_parser_cls=sybil_extras.parsers.norg.custom_directive_skip.CustomDirectiveSkipParser,
    code_block_parser_cls=sybil_extras.parsers.norg.codeblock.CodeBlockParser,
    group_parser_cls=sybil_extras.parsers.norg.grouped_source.GroupedSourceParser,
    group_all_parser_cls=sybil_extras.parsers.norg.group_all.GroupAllParser,
    sphinx_jinja_parser_cls=None,
    code_block_builder=_norg_code_block,
    directive_builder=_norg_directive,
    jinja_block_builder=None,
)

ALL_LANGUAGES: tuple[MarkupLanguage, ...] = (
    MYST,
    MYST_PERCENT_COMMENTS,
    RESTRUCTUREDTEXT,
    MARKDOWN,
    MDX,
    DJOT,
    NORG,
)
