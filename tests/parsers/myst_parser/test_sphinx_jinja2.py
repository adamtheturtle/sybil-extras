"""Coverage tests for the myst-parser sphinx-jinja2 parser.

The main sphinx-jinja2 test is parametrized in
tests/parsers/test_sphinx_jinja2.py.
"""

import textwrap
from pathlib import Path

import pytest
from sybil import Sybil

from sybil_extras.evaluators.no_op import NoOpEvaluator
from sybil_extras.parsers.myst_parser.sphinx_jinja2 import (
    SphinxJinja2Parser,
)


@pytest.mark.parametrize(
    argnames=("options", "expected"),
    argvalues=(
        (
            ':ctx: {"name": "World"}\n:custom-option: true\n:flag:\n',
            {
                "ctx": '{"name": "World"}',
                "custom-option": "true",
                "flag": "",
            },
        ),
        (
            '---\nctx: {"name": "World"}\ncustom-option: true\nflag:\n---\n',
            {
                "ctx": '{"name": "World"}',
                "custom-option": "true",
                "flag": "",
            },
        ),
        (
            "---\ncustom-option: |\n  first line\n  second line\n---\n",
            {"custom-option": "first line\nsecond line"},
        ),
    ),
)
def test_directive_options_and_exact_body(
    *, tmp_path: Path, options: str, expected: dict[str, str]
) -> None:
    """MyST extracts arbitrary string options without changing the
    body.
    """
    body = "Hello {{ name }}!  \n\n\n"
    path = tmp_path / "example.md"
    _ = path.write_text(
        data=f"```{{jinja}} named-context\n{options}\n{body}```\n",
        encoding="utf-8",
    )
    parser = SphinxJinja2Parser(evaluator=NoOpEvaluator())
    (example,) = Sybil(parsers=[parser]).parse(path=path).examples()

    assert example.parsed == body
    assert example.region.lexemes["options"] == expected
    assert example.region.lexemes["arguments"] == "named-context"


def test_nested_colon_fence_body(*, tmp_path: Path) -> None:
    """A colon fence immediately after options starts template content."""
    body = ":::{note}\n{{ message }}\n:::\n"
    path = tmp_path / "example.md"
    _ = path.write_text(
        data=f"```{{jinja}}\n:custom: value\n{body}```\n",
        encoding="utf-8",
    )
    parser = SphinxJinja2Parser(evaluator=NoOpEvaluator())
    (example,) = Sybil(parsers=[parser]).parse(path=path).examples()

    assert example.parsed == body
    assert example.region.lexemes["options"] == {"custom": "value"}


def test_non_jinja_fences_ignored(*, tmp_path: Path) -> None:
    """Non-jinja fence blocks and non-fence tokens are skipped."""
    content = textwrap.dedent(
        text="""\
        # A heading

        Some paragraph text.

        ```python
        print("hello")
        ```

        ```{jinja}
        Body here
        ```
        """
    )

    test_document = tmp_path / "test.md"
    _ = test_document.write_text(data=content, encoding="utf-8")

    parser = SphinxJinja2Parser(evaluator=NoOpEvaluator())
    sybil = Sybil(parsers=[parser])
    document = sybil.parse(path=test_document)

    (example,) = document.examples()
    assert example.parsed == "Body here\n"


def test_jinja_block_at_eof(*, tmp_path: Path) -> None:
    """A jinja block at the very end of a document is parsed."""
    content = "```{jinja}\nBody\n```"

    test_document = tmp_path / "test.md"
    _ = test_document.write_text(data=content, encoding="utf-8")

    parser = SphinxJinja2Parser(evaluator=NoOpEvaluator())
    sybil = Sybil(parsers=[parser])
    document = sybil.parse(path=test_document)

    (example,) = document.examples()
    assert example.parsed == "Body\n"


def test_options_with_blank_body(*, tmp_path: Path) -> None:
    """A jinja block with options and only blank lines for body."""
    content = textwrap.dedent(
        text="""\
        ```{jinja}
        :ctx: {"name": "World"}


        ```
        """
    )

    test_document = tmp_path / "test.md"
    _ = test_document.write_text(data=content, encoding="utf-8")

    parser = SphinxJinja2Parser(evaluator=NoOpEvaluator())
    sybil = Sybil(parsers=[parser])
    document = sybil.parse(path=test_document)

    (example,) = document.examples()
    assert example.parsed == ""
    assert example.region.lexemes["options"] == {
        "ctx": '{"name": "World"}',
    }


def test_options_with_many_blank_lines_body(*, tmp_path: Path) -> None:
    """A jinja block with options and multiple blank lines for body."""
    content = textwrap.dedent(
        text="""\
        ```{jinja}
        :ctx: {"name": "World"}



        ```
        """
    )

    test_document = tmp_path / "test.md"
    _ = test_document.write_text(data=content, encoding="utf-8")

    parser = SphinxJinja2Parser(evaluator=NoOpEvaluator())
    sybil = Sybil(parsers=[parser])
    document = sybil.parse(path=test_document)

    (example,) = document.examples()
    assert example.parsed == ""
    assert example.region.lexemes["options"] == {
        "ctx": '{"name": "World"}',
    }
