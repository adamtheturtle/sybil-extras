"""
Tests for the group parser for reST.
"""

from pathlib import Path
from textwrap import dedent

from sybil import Sybil
from sybil.parsers.rest.codeblock import PythonCodeBlockParser

from sybil_extras.parsers.rest.group import GroupParser


def test_group(tmp_path: Path) -> None:
    """
    Test that the group parser groups examples.
    """
    content = """\

    .. code-block:: python

        x = []

    .. group: start

    .. code-block:: python

        x = [*x, 2]

    .. code-block:: python

        x = [*x, 3]

    .. group: end

    .. code-block:: python

        x = [*x, 4]
    """

    test_document = tmp_path / "test.rst"
    test_document.write_text(data=content, encoding="utf-8")

    group_parser = GroupParser(directive="group")
    code_parser = PythonCodeBlockParser()

    sybil = Sybil(parsers=[code_parser, group_parser])
    document = sybil.parse(path=test_document)

    for example in document.examples():
        example.evaluate()

    assert document.namespace["x"] == [2, 3, 4]

    parsed_examples = [example.parsed for example in document.examples()]
    expected = dedent(
        text="""\
        x = [*x, 2]
        x = [*x, 3]
        """
    )
    assert expected in parsed_examples
