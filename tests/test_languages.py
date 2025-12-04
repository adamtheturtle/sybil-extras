"""
Tests for the languages module.
"""

import textwrap
from pathlib import Path

import pytest
from sybil import Sybil
from sybil.evaluators.python import PythonEvaluator

from sybil_extras.evaluators.block_accumulator import (
    BlockAccumulatorEvaluator,
)
from sybil_extras.languages import (
    MARKDOWN,
    MYST,
    RESTRUCTUREDTEXT,
    MarkupLanguage,
)


@pytest.mark.parametrize(
    argnames=("language", "content", "expected_namespace"),
    argvalues=[
        pytest.param(
            MYST,
            textwrap.dedent(
                text="""\
                ```python
                x = 1
                ```
                """
            ),
            {"x": 1},
            id="myst-code-block",
        ),
        pytest.param(
            RESTRUCTUREDTEXT,
            textwrap.dedent(
                text="""\
                .. code-block:: python

                   x = 2
                """
            ),
            {"x": 2},
            id="rest-code-block",
        ),
        pytest.param(
            MARKDOWN,
            textwrap.dedent(
                text="""\
                ```python
                x = 3
                ```
                """
            ),
            {"x": 3},
            id="markdown-code-block",
        ),
    ],
)
def test_code_block_parser(
    language: MarkupLanguage,
    content: str,
    expected_namespace: dict[str, object],
    tmp_path: Path,
) -> None:
    """
    Test that each language's code block parser works correctly.
    """
    extension = ".md" if language in {MYST, MARKDOWN} else ".rst"
    test_document = tmp_path / f"test{extension}"
    test_document.write_text(data=content, encoding="utf-8")

    parser = language.code_block_parser_cls(
        language="python",
        evaluator=PythonEvaluator(),
    )
    sybil = Sybil(parsers=[parser])
    document = sybil.parse(path=test_document)

    for example in document.examples():
        example.evaluate()

    assert document.namespace == expected_namespace


@pytest.mark.parametrize(
    argnames=("language", "skip_directive_content"),
    argvalues=[
        pytest.param(
            MYST,
            textwrap.dedent(
                text="""\
                % skip: next

                ```python
                x = 1
                ```
                """
            ),
            id="myst-skip",
        ),
        pytest.param(
            RESTRUCTUREDTEXT,
            textwrap.dedent(
                text="""\
                .. skip: next

                .. code-block:: python

                   x = 2
                """
            ),
            id="rest-skip",
        ),
        pytest.param(
            MARKDOWN,
            textwrap.dedent(
                text="""\
                <!--- skip: next -->

                ```python
                x = 3
                ```
                """
            ),
            id="markdown-skip",
        ),
    ],
)
def test_skip_parser(
    language: MarkupLanguage,
    skip_directive_content: str,
    tmp_path: Path,
) -> None:
    """
    Test that each language's skip parser works correctly.
    """
    extension = ".md" if language in {MYST, MARKDOWN} else ".rst"
    test_document = tmp_path / f"test{extension}"
    test_document.write_text(data=skip_directive_content, encoding="utf-8")

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
    argnames=("language", "grouped_content", "expected_result"),
    argvalues=[
        pytest.param(
            MYST,
            textwrap.dedent(
                text="""\
                <!--- group: start -->

                ```python
                x = 1
                ```

                ```python
                x = x + 1
                ```

                <!--- group: end -->
                """
            ),
            ["x = 1\n\n\n\nx = x + 1\n"],
            id="myst-grouped",
        ),
        pytest.param(
            RESTRUCTUREDTEXT,
            textwrap.dedent(
                text="""\
                .. group: start

                .. code-block:: python

                   x = 1

                .. code-block:: python

                   x = x + 1

                .. group: end
                """
            ),
            ["x = 1\n\n\n\nx = x + 1\n"],
            id="rest-grouped",
        ),
        pytest.param(
            MARKDOWN,
            textwrap.dedent(
                text="""\
                <!--- group: start -->

                ```python
                x = 1
                ```

                ```python
                x = x + 1
                ```

                <!--- group: end -->
                """
            ),
            ["x = 1\n\n\n\nx = x + 1\n"],
            id="markdown-grouped",
        ),
    ],
)
def test_group_parser(
    language: MarkupLanguage,
    grouped_content: str,
    expected_result: list[str],
    tmp_path: Path,
) -> None:
    """
    Test that each language's group parser works correctly.
    """
    extension = ".md" if language in {MYST, MARKDOWN} else ".rst"
    test_document = tmp_path / f"test{extension}"
    test_document.write_text(data=grouped_content, encoding="utf-8")

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

    assert document.namespace["blocks"] == expected_result


@pytest.mark.parametrize(
    argnames=("language", "jinja_content"),
    argvalues=[
        pytest.param(
            MYST,
            textwrap.dedent(
                text="""\
                ```{jinja}
                {{ 1 + 1 }}
                ```
                """
            ),
            id="myst-jinja",
        ),
        pytest.param(
            RESTRUCTUREDTEXT,
            textwrap.dedent(
                text="""\
                .. jinja::

                   {{ 1 + 1 }}
                """
            ),
            id="rest-jinja",
        ),
    ],
)
def test_sphinx_jinja_parser(
    language: MarkupLanguage,
    jinja_content: str,
    tmp_path: Path,
) -> None:
    """
    Test that each language's sphinx-jinja parser works correctly.
    """
    assert language.sphinx_jinja_parser_cls is not None

    extension = ".md" if language == MYST else ".rst"
    test_document = tmp_path / f"test{extension}"
    test_document.write_text(data=jinja_content, encoding="utf-8")

    def jinja_evaluator(example: object) -> None:
        """
        A simple evaluator for jinja blocks.
        """

    jinja_parser = language.sphinx_jinja_parser_cls(evaluator=jinja_evaluator)
    sybil = Sybil(parsers=[jinja_parser])
    document = sybil.parse(path=test_document)

    # Just verify that the parser can parse the document
    examples = list(document.examples())
    assert len(examples) == 1


def test_markdown_no_sphinx_jinja() -> None:
    """
    Test that Markdown does not have a sphinx-jinja parser.
    """
    assert MARKDOWN.sphinx_jinja_parser_cls is None


def test_language_names() -> None:
    """
    Test that languages have the expected names.
    """
    assert MYST.name == "MyST"
    assert RESTRUCTUREDTEXT.name == "reStructuredText"
    assert MARKDOWN.name == "Markdown"
