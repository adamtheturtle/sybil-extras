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
    The group parser groups examples.
    """
    content = """\

    .. code-block:: python

        x = []

    .. group: start

    .. code-block:: python

        x = [*x, 1]

    .. code-block:: python

        x = [*x, 2]

    .. group: end

    .. code-block:: python

        x = [*x, 3]

    """

    test_document = tmp_path / "test.rst"
    test_document.write_text(data=content, encoding="utf-8")

    group_parser = GroupParser(directive="group")
    code_parser = PythonCodeBlockParser()

    sybil = Sybil(parsers=[code_parser, group_parser])
    document = sybil.parse(path=test_document)

    for example in document.examples():
        example.evaluate()

    parsed_examples = [example.parsed for example in document.examples()]
    expected = [
        "x = []\n",
        dedent(
            text="""\
            x = [*x, 1]

            x = [*x, 2]
            """
        ),
        "x = [*x, 3]\n",
    ]
    assert parsed_examples == expected

    assert document.namespace["x"] == [1, 2, 3]


def test_nothing_after_group(tmp_path: Path) -> None:
    """
    The group parser groups examples even at the end of a document.
    """
    content = """\

    .. code-block:: python

        x = []

    .. group: start

    .. code-block:: python

        x = [*x, 1]

    .. code-block:: python

        x = [*x, 2]

    .. group: end
    """

    test_document = tmp_path / "test.rst"
    test_document.write_text(data=content, encoding="utf-8")

    group_parser = GroupParser(directive="group")
    code_parser = PythonCodeBlockParser()

    sybil = Sybil(parsers=[code_parser, group_parser])
    document = sybil.parse(path=test_document)

    for example in document.examples():
        example.evaluate()

    parsed_examples = [example.parsed for example in document.examples()]
    expected = [
        "x = []\n",
        dedent(
            text="""\
            x = [*x, 1]

            x = [*x, 2]
            """
        ),
    ]
    assert parsed_examples == expected

    assert document.namespace["x"] == [1, 2]


def test_empty_group(tmp_path: Path) -> None:
    """
    The group parser groups examples even when the group is empty.
    """
    content = """\

    .. code-block:: python

        x = []

    .. group: start

    .. group: end

    .. code-block:: python

        x = [*x, 3]
    """

    test_document = tmp_path / "test.rst"
    test_document.write_text(data=content, encoding="utf-8")

    group_parser = GroupParser(directive="group")
    code_parser = PythonCodeBlockParser()

    sybil = Sybil(parsers=[code_parser, group_parser])
    document = sybil.parse(path=test_document)

    for example in document.examples():
        example.evaluate()

    parsed_examples = [example.parsed for example in document.examples()]
    expected = [
        "x = []\n",
        "x = [*x, 3]",
    ]
    assert parsed_examples == expected

    assert document.namespace["x"] == [3]


# TODO: With skips before / in the middle
# TODO: With end before start / without start
# TODO: With different evaluators in the middle
