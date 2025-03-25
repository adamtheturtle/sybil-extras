"""
Tests for the sphinx-jinja2 parser for reST.
"""

from pathlib import Path

from sybil import Sybil
from sybil.example import Example

from sybil_extras.parsers.rest.sphinx_jinja2 import SphinxJinja2Parser


def test_sphinx_jinja2(*, tmp_path: Path) -> None:
    """
    The sphinx-jinja2 parser extracts information from jinja blocks.
    """
    # These examples are taken from the sphinx-jinja2 documentation.
    content = """\
    .. jinja::
       :ctx: {"name": "World"}

       Hallo {{ name }}!

    .. jinja::
       :file: templates/example1.jinja
       :ctx: {"name": "World"}
    """

    test_document = tmp_path / "test.rst"
    test_document.write_text(data=content, encoding="utf-8")

    def evaluator(example: Example) -> None:
        breakpoint()

    parser = SphinxJinja2Parser(evaluator=evaluator)
    sybil = Sybil(parsers=[parser])
    document = sybil.parse(path=test_document)

    for example in document.examples():
        example.evaluate()


def test_write_with_shell_evaluator(*, tmp_path: Path) -> None:
    """
    It is possible to write to empty and non-empty jinja blocks.
    """
