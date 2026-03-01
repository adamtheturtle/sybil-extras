"""Tests for the sphinx-jinja2 parser using myst-parser."""

import textwrap
from pathlib import Path

from sybil import Sybil

from sybil_extras.evaluators.no_op import NoOpEvaluator
from sybil_extras.parsers.myst_parser.sphinx_jinja2 import (
    SphinxJinja2Parser,
)


def test_sphinx_jinja2(*, tmp_path: Path) -> None:
    """The ``SphinxJinja2Parser`` extracts information from
    sphinx-jinja2 blocks.
    """
    content = textwrap.dedent(
        text="""\
        ```{jinja}
        :ctx: {"name": "World"}

        Hallo {{ name }}!
        ```

        ```{jinja}
        :file: templates/example1.jinja
        :ctx: {"name": "World"}
        ```
        """
    )

    test_document = tmp_path / "test.md"
    test_document.write_text(data=content, encoding="utf-8")

    parser = SphinxJinja2Parser(evaluator=NoOpEvaluator())
    sybil = Sybil(parsers=[parser])
    document = sybil.parse(path=test_document)

    first_example, second_example = document.examples()
    assert first_example.parsed == "Hallo {{ name }}!\n"
    assert first_example.region.lexemes == {
        "directive": "jinja",
        "arguments": "",
        "source": "Hallo {{ name }}!\n",
        "options": {"ctx": '{"name": "World"}'},
    }
    first_example.evaluate()

    assert second_example.parsed == ""
    assert second_example.region.lexemes == {
        "directive": "jinja",
        "arguments": "",
        "source": "",
        "options": {
            "file": "templates/example1.jinja",
            "ctx": '{"name": "World"}',
        },
    }


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
    test_document.write_text(data=content, encoding="utf-8")

    parser = SphinxJinja2Parser(evaluator=NoOpEvaluator())
    sybil = Sybil(parsers=[parser])
    document = sybil.parse(path=test_document)

    (example,) = document.examples()
    assert example.parsed == "Body here\n"


def test_jinja_block_at_eof(*, tmp_path: Path) -> None:
    """A jinja block at the very end of a document is parsed."""
    content = "```{jinja}\nBody\n```"

    test_document = tmp_path / "test.md"
    test_document.write_text(data=content, encoding="utf-8")

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
    test_document.write_text(data=content, encoding="utf-8")

    parser = SphinxJinja2Parser(evaluator=NoOpEvaluator())
    sybil = Sybil(parsers=[parser])
    document = sybil.parse(path=test_document)

    (example,) = document.examples()
    assert example.parsed == ""
    assert example.region.lexemes["options"] == {
        "ctx": '{"name": "World"}',
    }
