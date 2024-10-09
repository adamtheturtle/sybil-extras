"""
Tests for the custom directive skip parser for MyST.
"""

from pathlib import Path

from sybil import Sybil
from sybil.parsers.myst.codeblock import PythonCodeBlockParser

from sybil_extras.parsers.myst.custom_directive_skip import (
    CustomDirectiveSkipParser,
)


def test_skip(tmp_path: Path) -> None:
    """
    Test that the custom directive skip parser skips the directive.
    """
    content = """\
    Example

    ```python
    x = []
    ```

    <!--- custom-skip: next -->

    ```python
    x = [*x, 2]
    ```

    ```python
    x = [*x, 3]
    ```

    % custom-skip: next

    ```python
    x = [*x, 4]
    ```
    """

    test_document = tmp_path / "test.md"
    test_document.write_text(data=content, encoding="utf-8")

    skip_parser = CustomDirectiveSkipParser(directive="custom-skip")
    code_parser = PythonCodeBlockParser()

    sybil = Sybil(parsers=[code_parser, skip_parser])
    document = sybil.parse(path=test_document)
    for example in document.examples():
        example.evaluate()

    assert document.namespace["x"] == [3]
