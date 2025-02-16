"""
Tests for the group parser for MyST.
"""

from pathlib import Path

import pytest
from sybil import Sybil
from sybil.example import Example
from sybil.parsers.myst.codeblock import CodeBlockParser
from sybil.parsers.myst.skip import SkipParser

from sybil_extras.parsers.myst.grouped_code_block import GroupedCodeBlockParser


def test_group(tmp_path: Path) -> None:
    """
    The group parser groups examples.
    """
    content = """\

    ```python
    x = []
    ```

    <!--- group: start -->

    ```python
    x = [*x, 1]
    ```

    ```python
     x = [*x, 2]
    ```

    <!--- group: end -->

    ```python
     x = [*x, 3]
    ```

    """

    test_document = tmp_path / "test.md"
    test_document.write_text(data=content, encoding="utf-8")

    def evaluator(example: Example) -> None:
        """
        Add code block content to the namespace.
        """
        existing_blocks = example.document.namespace.get("blocks", [])
        example.document.namespace["blocks"] = [
            *existing_blocks,
            example.parsed,
        ]

    group_parser = GroupedCodeBlockParser(
        directive="group",
        evaluator=evaluator,
    )
    code_block_parser = CodeBlockParser(language="python", evaluator=evaluator)

    sybil = Sybil(parsers=[code_block_parser, group_parser])
    document = sybil.parse(path=test_document)

    for example in document.examples():
        example.evaluate()

    assert document.namespace["blocks"] == [
        "x = []\n",
        "x = [*x, 1]\nx = [*x, 2]\n",
        "x = [*x, 3]\n",
    ]


def test_nothing_after_group(tmp_path: Path) -> None:
    """
    The group parser groups examples even at the end of a document.
    """
    content = """\

    ```python
     x = []
    ```

    <!--- group: start -->

    ```python
     x = [*x, 1]
    ```

    ```python
     x = [*x, 2]
    ```

    <!--- group: end -->
    """

    test_document = tmp_path / "test.md"
    test_document.write_text(data=content, encoding="utf-8")

    def evaluator(example: Example) -> None:
        """
        Add code block content to the namespace.
        """
        existing_blocks = example.document.namespace.get("blocks", [])
        example.document.namespace["blocks"] = [
            *existing_blocks,
            example.parsed,
        ]

    group_parser = GroupedCodeBlockParser(
        directive="group",
        evaluator=evaluator,
    )
    code_block_parser = CodeBlockParser(language="python", evaluator=evaluator)

    sybil = Sybil(parsers=[code_block_parser, group_parser])
    document = sybil.parse(path=test_document)

    for example in document.examples():
        example.evaluate()

    assert document.namespace["blocks"] == [
        "x = []\n",
        "x = [*x, 1]\nx = [*x, 2]\n",
    ]


def test_empty_group(tmp_path: Path) -> None:
    """
    The group parser groups examples even when the group is empty.
    """
    content = """\

    ```python
     x = []
    ```

    <!--- group: start -->

    <!--- group: end -->

    ```python
     x = [*x, 3]
    ```
    """

    test_document = tmp_path / "test.md"
    test_document.write_text(data=content, encoding="utf-8")

    def evaluator(example: Example) -> None:
        """
        Add code block content to the namespace.
        """
        existing_blocks = example.document.namespace.get("blocks", [])
        example.document.namespace["blocks"] = [
            *existing_blocks,
            example.parsed,
        ]

    group_parser = GroupedCodeBlockParser(
        directive="group",
        evaluator=evaluator,
    )
    code_block_parser = CodeBlockParser(language="python", evaluator=evaluator)

    sybil = Sybil(parsers=[code_block_parser, group_parser])
    document = sybil.parse(path=test_document)

    for example in document.examples():
        example.evaluate()

    assert document.namespace["blocks"] == [
        "x = []\n",
        "x = [*x, 3]\n",
    ]


def test_group_with_skip(tmp_path: Path) -> None:
    """
    Skip directives are respected within a group.
    """
    content = """\

    ```python
     x = []
    ```

    <!--- group: start -->

    ```python
     x = [*x, 1]
    ```

    <!--- skip: next -->

    ```python
     x = [*x, 2]
    ```

    <!--- group: end -->

    ```python
     x = [*x, 3]
    ```
    """

    test_document = tmp_path / "test.md"
    test_document.write_text(data=content, encoding="utf-8")

    def evaluator(example: Example) -> None:
        """
        Add code block content to the namespace.
        """
        existing_blocks = example.document.namespace.get("blocks", [])
        example.document.namespace["blocks"] = [
            *existing_blocks,
            example.parsed,
        ]

    group_parser = GroupedCodeBlockParser(
        directive="group",
        evaluator=evaluator,
    )
    code_block_parser = CodeBlockParser(language="python", evaluator=evaluator)
    skip_parser = SkipParser()

    sybil = Sybil(parsers=[code_block_parser, skip_parser, group_parser])
    document = sybil.parse(path=test_document)

    for example in document.examples():
        example.evaluate()

    assert document.namespace["blocks"] == [
        "x = []\n",
        "x = [*x, 1]\n",
        "x = [*x, 3]\n",
    ]


def test_no_argument(tmp_path: Path) -> None:
    """
    An error is raised when a group directive has no arguments.
    """
    content = """\
    <!--- group -->

    <!--- group: end -->
    """

    test_document = tmp_path / "test.md"
    test_document.write_text(data=content, encoding="utf-8")

    def evaluator(_: Example) -> None:
        """
        No-op evaluator.
        """

    group_parser = GroupedCodeBlockParser(
        directive="group",
        evaluator=evaluator,
    )

    sybil = Sybil(parsers=[group_parser])
    expected_error = r"missing arguments to group"
    with pytest.raises(expected_exception=ValueError, match=expected_error):
        sybil.parse(path=test_document)


def test_end_only(tmp_path: Path) -> None:
    """
    An error is raised when a group end directive is given with no start.
    """
    content = """\
    <!--- group: end -->
    """

    test_document = tmp_path / "test.md"
    test_document.write_text(data=content, encoding="utf-8")

    def evaluator(_: Example) -> None:
        """
        No-op evaluator.
        """

    group_parser = GroupedCodeBlockParser(
        directive="group",
        evaluator=evaluator,
    )

    sybil = Sybil(parsers=[group_parser])
    document = sybil.parse(path=test_document)

    (example,) = document.examples()
    match = r"'group: end' must follow 'group: start'"
    with pytest.raises(expected_exception=ValueError, match=match):
        example.evaluate()


def test_start_after_start(tmp_path: Path) -> None:
    """
    An error is raised when a group start directive is given after another
    start.
    """
    content = """\
    <!--- group: start -->

    <!--- group: start -->
    """

    test_document = tmp_path / "test.rst"
    test_document.write_text(data=content, encoding="utf-8")

    def evaluator(_: Example) -> None:
        """
        No-op evaluator.
        """

    group_parser = GroupedCodeBlockParser(
        directive="group",
        evaluator=evaluator,
    )

    sybil = Sybil(parsers=[group_parser])
    document = sybil.parse(path=test_document)

    (first_start_example, second_start_example) = document.examples()

    first_start_example.evaluate()

    match = r"'group: start' must be followed by 'group: end'"
    with pytest.raises(expected_exception=ValueError, match=match):
        second_start_example.evaluate()
