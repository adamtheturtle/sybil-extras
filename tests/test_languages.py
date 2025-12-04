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
    MARKDOWN,
    MYST,
    RESTRUCTUREDTEXT,
    MarkupLanguage,
)
from tests.helpers import document_data, join_markup, write_document


@pytest.mark.parametrize(
    argnames=("language", "value"),
    argvalues=[
        pytest.param(MYST, 1, id="myst-code-block"),
        pytest.param(RESTRUCTUREDTEXT, 2, id="rest-code-block"),
        pytest.param(MARKDOWN, 3, id="markdown-code-block"),
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
    content = language.code_block(code=code)
    test_document = write_document(
        language=language,
        directory=tmp_path,
        data=document_data(language=language, content=content),
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
        pytest.param(RESTRUCTUREDTEXT, 2, id="rest-skip"),
        pytest.param(MARKDOWN, 3, id="markdown-skip"),
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
    content = join_markup(
        language.directive(directive="skip", argument="next"),
        language.code_block(code=f"x = {value}"),
    )
    test_document = write_document(
        language=language,
        directory=tmp_path,
        data=document_data(language=language, content=content),
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
        pytest.param(RESTRUCTUREDTEXT, id="rest-empty"),
        pytest.param(MARKDOWN, id="markdown-empty"),
    ],
)
def test_code_block_empty(language: MarkupLanguage) -> None:
    """
    Code block builders handle empty content.
    """
    block = language.code_block(code="")
    assert block


@pytest.mark.parametrize(
    argnames=("language"),
    argvalues=[
        pytest.param(MYST, id="myst-empty-doc"),
        pytest.param(RESTRUCTUREDTEXT, id="rest-empty-doc"),
        pytest.param(MARKDOWN, id="markdown-empty-doc"),
    ],
)
def test_write_document_empty(
    language: MarkupLanguage, tmp_path: Path
) -> None:
    """
    Writing an empty document does not add trailing newlines.
    """
    path = write_document(
        language=language,
        directory=tmp_path,
        data=document_data(language=language, content=""),
        stem="empty",
    )
    assert path.read_text(encoding="utf-8") == ""


@pytest.mark.parametrize(
    argnames=("language"),
    argvalues=[
        pytest.param(MYST, id="myst-grouped"),
        pytest.param(RESTRUCTUREDTEXT, id="rest-grouped"),
        pytest.param(MARKDOWN, id="markdown-grouped"),
    ],
)
def test_group_parser(
    language: MarkupLanguage,
    tmp_path: Path,
) -> None:
    """
    Test that each language's group parser works correctly.
    """
    content = join_markup(
        language.directive(directive="group", argument="start"),
        language.code_block(code="x = 1"),
        language.code_block(code="x = x + 1"),
        language.directive(directive="group", argument="end"),
    )
    test_document = write_document(
        language=language,
        directory=tmp_path,
        data=document_data(language=language, content=content),
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

    assert document.namespace["blocks"] == ["x = 1\n\n\n\nx = x + 1\n"]


@pytest.mark.parametrize(
    argnames=("language"),
    argvalues=[
        pytest.param(MYST, id="myst-jinja"),
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

    jinja_content = language.jinja_block(body="{{ 1 + 1 }}")
    test_document = write_document(
        language=language,
        directory=tmp_path,
        data=document_data(language=language, content=jinja_content),
    )

    jinja_parser = language.sphinx_jinja_parser_cls(evaluator=NoOpEvaluator())
    sybil = Sybil(parsers=[jinja_parser])
    document = sybil.parse(path=test_document)

    examples = list(document.examples())
    assert len(examples) == 1


def test_markdown_no_sphinx_jinja() -> None:
    """
    Test that Markdown does not have a sphinx-jinja parser.
    """
    assert MARKDOWN.sphinx_jinja_parser_cls is None
    with pytest.raises(
        expected_exception=ValueError,
        match="does not support sphinx-jinja blocks",
    ):
        MARKDOWN.jinja_block(body="{{ 1 }}")


def test_language_names() -> None:
    """
    Test that languages have the expected names.
    """
    assert MYST.name == "MyST"
    assert RESTRUCTUREDTEXT.name == "reStructuredText"
    assert MARKDOWN.name == "Markdown"
