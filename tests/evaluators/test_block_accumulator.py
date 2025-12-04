"""
Tests for the BlockAccumulatorEvaluator.
"""

from pathlib import Path

from sybil import Sybil
from sybil.parsers.rest.codeblock import CodeBlockParser

from sybil_extras.evaluators.block_accumulator import BlockAccumulatorEvaluator


def test_accumulates_blocks(tmp_path: Path) -> None:
    """
    The evaluator accumulates parsed code blocks in the namespace.
    """
    content = """\
.. code-block:: python

   x = 1

.. code-block:: python

   y = 2

.. code-block:: python

   z = 3
"""
    test_document = tmp_path / "test.rst"
    test_document.write_text(data=content, encoding="utf-8")

    evaluator = BlockAccumulatorEvaluator(namespace_key="blocks")
    parser = CodeBlockParser(language="python", evaluator=evaluator)
    sybil = Sybil(parsers=[parser])
    document = sybil.parse(path=test_document)

    for example in document.examples():
        example.evaluate()

    assert document.namespace["blocks"] == ["x = 1\n", "y = 2\n", "z = 3"]


def test_custom_namespace_key(tmp_path: Path) -> None:
    """
    The evaluator can use a custom namespace key.
    """
    content = """\
.. code-block:: python

   x = 1

.. code-block:: python

   y = 2
"""
    test_document = tmp_path / "test.rst"
    test_document.write_text(data=content, encoding="utf-8")

    evaluator = BlockAccumulatorEvaluator(namespace_key="custom_key")
    parser = CodeBlockParser(language="python", evaluator=evaluator)
    sybil = Sybil(parsers=[parser])
    document = sybil.parse(path=test_document)

    for example in document.examples():
        example.evaluate()

    assert document.namespace["custom_key"] == ["x = 1\n", "y = 2"]
    assert "blocks" not in document.namespace


def test_single_block(tmp_path: Path) -> None:
    """
    The evaluator handles a single code block.
    """
    content = """\
.. code-block:: python

   x = 1
"""
    test_document = tmp_path / "test.rst"
    test_document.write_text(data=content, encoding="utf-8")

    evaluator = BlockAccumulatorEvaluator(namespace_key="blocks")
    parser = CodeBlockParser(language="python", evaluator=evaluator)
    sybil = Sybil(parsers=[parser])
    document = sybil.parse(path=test_document)

    for example in document.examples():
        example.evaluate()

    assert document.namespace["blocks"] == ["x = 1"]


def test_preserves_content(tmp_path: Path) -> None:
    """
    The evaluator preserves the exact content of code blocks.
    """
    content = """\
.. code-block:: python

   # Comment with special chars: !@#$%^&*()
   x = "string with 'quotes'"
   y = '''triple
   quoted
   string'''
"""
    test_document = tmp_path / "test.rst"
    test_document.write_text(data=content, encoding="utf-8")

    evaluator = BlockAccumulatorEvaluator(namespace_key="blocks")
    parser = CodeBlockParser(language="python", evaluator=evaluator)
    sybil = Sybil(parsers=[parser])
    document = sybil.parse(path=test_document)

    for example in document.examples():
        example.evaluate()

    expected_content = """\
# Comment with special chars: !@#$%^&*()
x = "string with 'quotes'"
y = '''triple
quoted
string'''"""
    assert document.namespace["blocks"] == [expected_content]
