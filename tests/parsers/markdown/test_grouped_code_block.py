"""
Tests for the group parser for Markdown.
"""

from pathlib import Path

import pytest
from sybil import Sybil
from sybil.example import Example
from sybil.parsers.markdown.codeblock import (
    CodeBlockParser,
)
from sybil.parsers.markdown.skip import SkipParser

from sybil_extras.parsers.markdown.grouped_code_block import (
    GroupedCodeBlockParser,
)


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

    test_document = tmp_path / "test.rst"
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
    code_parser = CodeBlockParser(language="python", evaluator=evaluator)

    sybil = Sybil(parsers=[code_parser, group_parser])
    document = sybil.parse(path=test_document)

    for example in document.examples():
        example.evaluate()

    assert document.namespace["blocks"] == [
        "x = []\n",
        "x = [*x, 1]\n\nx = [*x, 2]\n",
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

    test_document = tmp_path / "test.rst"
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
    code_parser = CodeBlockParser(language="python", evaluator=evaluator)

    sybil = Sybil(parsers=[code_parser, group_parser])
    document = sybil.parse(path=test_document)

    for example in document.examples():
        example.evaluate()

    assert document.namespace["blocks"] == [
        "x = []\n",
        "x = [*x, 1]\n\nx = [*x, 2]\n",
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

    test_document = tmp_path / "test.rst"
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
    code_parser = CodeBlockParser(language="python", evaluator=evaluator)

    sybil = Sybil(parsers=[code_parser, group_parser])
    document = sybil.parse(path=test_document)

    for example in document.examples():
        example.evaluate()

    assert document.namespace["blocks"] == [
        "x = []\n",
        "x = [*x, 3]\n",
    ]


def test_group_with_skip(tmp_path: Path) -> None:
    """
    An error is raised when a group contains a skip.
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

    test_document = tmp_path / "test.rst"
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
    code_parser = CodeBlockParser(language="python")
    skip_parser = SkipParser()

    sybil = Sybil(parsers=[code_parser, skip_parser, group_parser])
    with pytest.raises(
        expected_exception=ValueError,
        match="All sub-regions of a group must have the same evaluator.",
    ):
        sybil.parse(path=test_document)
