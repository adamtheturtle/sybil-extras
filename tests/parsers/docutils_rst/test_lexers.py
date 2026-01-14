"""
Tests for the docutils_rst lexers.
"""

from pathlib import Path

from sybil import Sybil
from sybil.evaluators.python import PythonEvaluator

from sybil_extras.parsers.docutils_rst.codeblock import CodeBlockParser
from sybil_extras.parsers.docutils_rst.custom_directive_skip import (
    CustomDirectiveSkipParser,
)


def test_directive_in_comment(tmp_path: Path) -> None:
    """
    Directive in an RST comment is recognized.
    """
    content = """
.. custom-skip: next

.. code-block:: python

   x = 1
"""
    test_file = tmp_path / "test.rst"
    test_file.write_text(data=content, encoding="utf-8")

    skip_parser = CustomDirectiveSkipParser(directive="custom-skip")
    code_parser = CodeBlockParser(
        language="python",
        evaluator=PythonEvaluator(),
    )
    sybil = Sybil(parsers=[code_parser, skip_parser])
    document = sybil.parse(path=test_file)

    # Evaluate all examples
    for example in document.examples():
        example.evaluate()

    # The skip directive should have been recognized and the code block
    # should have been skipped, so x should not be in the namespace
    assert "x" not in document.namespace


def test_directive_without_colon(tmp_path: Path) -> None:
    """
    Directive without a colon is also recognized.
    """
    content = """
.. custom-skip next

.. code-block:: python

   x = 1
"""
    test_file = tmp_path / "test.rst"
    test_file.write_text(data=content, encoding="utf-8")

    skip_parser = CustomDirectiveSkipParser(directive="custom-skip")
    code_parser = CodeBlockParser(
        language="python",
        evaluator=PythonEvaluator(),
    )
    sybil = Sybil(parsers=[code_parser, skip_parser])
    document = sybil.parse(path=test_file)

    # Evaluate all examples
    for example in document.examples():
        example.evaluate()

    # The skip directive should have been recognized and the code block
    # should have been skipped, so x should not be in the namespace
    assert "x" not in document.namespace
