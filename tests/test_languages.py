"""
Tests for the languages module.
"""

from pathlib import Path

import pytest
from sybil import Sybil
from sybil.evaluators.python import PythonEvaluator

from sybil_extras.evaluators.block_accumulator import (
    BlockAccumulatorEvaluator,
)
from sybil_extras.evaluators.no_op import NoOpEvaluator
from sybil_extras.languages import (
    DJOT,
    MARKDOWN,
    MDX,
    MYST,
    MYST_PERCENT_COMMENTS,
    NORG,
    RESTRUCTUREDTEXT,
    MarkupLanguage,
)


@pytest.mark.parametrize(
    argnames=("language", "value"),
    argvalues=[
        pytest.param(MYST, 1, id="myst-code-block"),
        pytest.param(
            MYST_PERCENT_COMMENTS,
            2,
            id="myst-percent-code-block",
        ),
        pytest.param(RESTRUCTUREDTEXT, 3, id="rest-code-block"),
        pytest.param(MARKDOWN, 4, id="markdown-code-block"),
        pytest.param(MDX, 5, id="mdx-code-block"),
        pytest.param(DJOT, 6, id="djot-code-block"),
        pytest.param(NORG, 7, id="norg-code-block"),
    ],
)
def test_code_block_parser(
    language: MarkupLanguage,
    value: int,
    tmp_path: Path,
) -> None:
    """
    Test that each language's code block parser works correctly.
    """
    code = f"x = {value}"
    content = language.code_block_builder(code=code, language="python")
    test_document = tmp_path / "test"
    test_document.write_text(
        data=f"{content}{language.markup_separator}",
        encoding="utf-8",
    )

    parser = language.code_block_parser_cls(
        language="python",
        evaluator=PythonEvaluator(),
    )
    sybil = Sybil(parsers=[parser])
    document = sybil.parse(path=test_document)

    for example in document.examples():
        example.evaluate()

    assert document.namespace == {"x": value}


@pytest.mark.parametrize(
    argnames=("language", "value"),
    argvalues=[
        pytest.param(MYST, 1, id="myst-skip"),
        pytest.param(
            MYST_PERCENT_COMMENTS,
            2,
            id="myst-percent-skip",
        ),
        pytest.param(RESTRUCTUREDTEXT, 3, id="rest-skip"),
        pytest.param(MARKDOWN, 4, id="markdown-skip"),
        pytest.param(MDX, 5, id="mdx-skip"),
        pytest.param(DJOT, 6, id="djot-skip"),
        pytest.param(NORG, 7, id="norg-skip"),
    ],
)
def test_skip_parser(
    language: MarkupLanguage,
    value: int,
    tmp_path: Path,
) -> None:
    """
    Test that each language's skip parser works correctly.
    """
    content = language.markup_separator.join(
        [
            language.directive_builder(directive="skip", argument="next"),
            language.code_block_builder(
                code=f"x = {value}", language="python"
            ),
        ]
    )
    test_document = tmp_path / "test"
    test_document.write_text(
        data=f"{content}{language.markup_separator}",
        encoding="utf-8",
    )

    skip_parser = language.skip_parser_cls(directive="skip")
    code_parser = language.code_block_parser_cls(
        language="python",
        evaluator=PythonEvaluator(),
    )
    sybil = Sybil(parsers=[code_parser, skip_parser])
    document = sybil.parse(path=test_document)

    for example in document.examples():
        example.evaluate()

    # The code block should be skipped
    assert not document.namespace


@pytest.mark.parametrize(
    argnames=("language"),
    argvalues=[
        pytest.param(MYST, id="myst-empty"),
        pytest.param(MYST_PERCENT_COMMENTS, id="myst-percent-empty"),
        pytest.param(RESTRUCTUREDTEXT, id="rest-empty"),
        pytest.param(MARKDOWN, id="markdown-empty"),
        pytest.param(MDX, id="mdx-empty"),
        pytest.param(DJOT, id="djot-empty"),
        pytest.param(NORG, id="norg-empty"),
    ],
)
def test_code_block_empty(language: MarkupLanguage) -> None:
    """
    Code block builders handle empty content.
    """
    block = language.code_block_builder(code="", language="python")
    assert block


@pytest.mark.parametrize(
    argnames=("language"),
    argvalues=[
        pytest.param(MYST, id="myst-grouped"),
        pytest.param(
            MYST_PERCENT_COMMENTS,
            id="myst-percent-grouped",
        ),
        pytest.param(RESTRUCTUREDTEXT, id="rest-grouped"),
        pytest.param(MARKDOWN, id="markdown-grouped"),
        pytest.param(MDX, id="mdx-grouped"),
        pytest.param(DJOT, id="djot-grouped"),
        pytest.param(NORG, id="norg-grouped"),
    ],
)
def test_group_parser(
    language: MarkupLanguage,
    tmp_path: Path,
) -> None:
    """
    Test that each language's group parser works correctly.
    """
    content = language.markup_separator.join(
        [
            language.directive_builder(directive="group", argument="start"),
            language.code_block_builder(code="x = 1", language="python"),
            language.code_block_builder(code="x = x + 1", language="python"),
            language.directive_builder(directive="group", argument="end"),
        ]
    )
    test_document = tmp_path / "test"
    test_document.write_text(
        data=f"{content}{language.markup_separator}",
        encoding="utf-8",
    )

    evaluator = BlockAccumulatorEvaluator(namespace_key="blocks")

    group_parser = language.group_parser_cls(
        directive="group",
        evaluator=evaluator,
        pad_groups=True,
    )
    code_block_parser = language.code_block_parser_cls(
        language="python",
        evaluator=evaluator,
    )
    sybil = Sybil(parsers=[code_block_parser, group_parser])
    document = sybil.parse(path=test_document)

    for example in document.examples():
        example.evaluate()

    separator_newlines = len(language.markup_separator)
    padding_newlines = separator_newlines + 1
    padding = "\n" * padding_newlines

    expected = f"x = 1\n{padding}x = x + 1\n"
    assert document.namespace["blocks"] == [expected]


@pytest.mark.parametrize(
    argnames=("language"),
    argvalues=[
        pytest.param(MYST, id="myst-jinja"),
        pytest.param(
            MYST_PERCENT_COMMENTS,
            id="myst-percent-jinja",
        ),
        pytest.param(RESTRUCTUREDTEXT, id="rest-jinja"),
    ],
)
def test_sphinx_jinja_parser(
    language: MarkupLanguage,
    tmp_path: Path,
) -> None:
    """
    Test that each language's sphinx-jinja parser works correctly.
    """
    assert language.sphinx_jinja_parser_cls is not None
    jinja_builder = language.jinja_block_builder
    assert jinja_builder is not None

    jinja_content = jinja_builder(body="{{ 1 + 1 }}")
    test_document = tmp_path / "test"
    test_document.write_text(
        data=f"{jinja_content}{language.markup_separator}",
        encoding="utf-8",
    )

    jinja_parser = language.sphinx_jinja_parser_cls(evaluator=NoOpEvaluator())
    sybil = Sybil(parsers=[jinja_parser])
    document = sybil.parse(path=test_document)

    examples = list(document.examples())
    assert len(examples) == 1


def test_markdown_no_sphinx_jinja() -> None:
    """
    Test that Markdown-like formats do not have a sphinx-jinja parser.
    """
    for language in (MARKDOWN, MDX, DJOT, NORG):
        assert language.sphinx_jinja_parser_cls is None
        assert language.jinja_block_builder is None


def test_language_names() -> None:
    """
    Test that languages have the expected names.
    """
    assert MYST.name == "MyST"
    assert MYST_PERCENT_COMMENTS.name == "MyST (percent comments)"
    assert RESTRUCTUREDTEXT.name == "reStructuredText"
    assert MARKDOWN.name == "Markdown"
    assert MDX.name == "MDX"
    assert DJOT.name == "Djot"
    assert NORG.name == "Norg"


def test_mdx_code_block_attributes(tmp_path: Path) -> None:
    """
    MDX code block parsers expose attributes from the info line.
    """
    mdx_content = (
        '```python title="example.py" group="setup"\nvalue = 7\n```\n'
    )
    test_document = tmp_path / "test.mdx"
    test_document.write_text(
        data=f"{mdx_content}{MDX.markup_separator}",
        encoding="utf-8",
    )

    parser = MDX.code_block_parser_cls(
        language="python",
        evaluator=PythonEvaluator(),
    )
    sybil = Sybil(parsers=[parser])
    document = sybil.parse(path=test_document)

    (example,) = document.examples()
    example.evaluate()

    assert document.namespace == {"value": 7}
    assert example.region.lexemes["attributes"] == {
        "title": "example.py",
        "group": "setup",
    }
