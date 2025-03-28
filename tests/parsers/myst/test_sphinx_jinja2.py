"""
Tests for the sphinx-jinja2 parser for MyST.
"""

from pathlib import Path

from sybil import Sybil

from sybil_extras.evaluators.no_op import NoOpEvaluator
from sybil_extras.parsers.myst.sphinx_jinja2 import SphinxJinja2Parser


def test_sphinx_jinja2(*, tmp_path: Path) -> None:
    """
    The ``SphinxJinja2Parser`` extracts information from sphinx-jinja2 blocks.
    """
    # These examples are taken from the sphinx-jinja2 documentation.
    content = """\
    ```{jinja}
    :ctx: {"name": "World"}

    Hallo {{ name }}!
    ```

    ```{jinja}
    :file: templates/example1.jinja
    :ctx: {"name": "World"}
    ```
    """

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
