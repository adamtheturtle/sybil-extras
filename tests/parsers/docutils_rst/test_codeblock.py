"""
Tests for the docutils_rst CodeBlockParser.
"""

from pathlib import Path

import pytest
from sybil import Sybil

from sybil_extras.evaluators.no_op import NoOpEvaluator
from sybil_extras.parsers.docutils_rst.codeblock import CodeBlockParser


def test_basic_code_block(tmp_path: Path) -> None:
    """
    Basic code blocks are parsed correctly.
    """
    content = """Some text

.. code-block:: python

   print("hello")
"""
    test_file = tmp_path / "test.rst"
    test_file.write_text(data=content, encoding="utf-8")

    parser = CodeBlockParser(language="python", evaluator=NoOpEvaluator())
    sybil = Sybil(parsers=[parser])
    document = sybil.parse(path=test_file)
    examples = list(document.examples())

    assert len(examples) == 1
    assert examples[0].parsed.text == 'print("hello")\n'


def test_multiple_code_blocks(tmp_path: Path) -> None:
    """
    Multiple code blocks are all parsed.
    """
    content = """Some text

.. code-block:: python

   x = 1

More text

.. code-block:: python

   y = 2
"""
    test_file = tmp_path / "test.rst"
    test_file.write_text(data=content, encoding="utf-8")

    parser = CodeBlockParser(language="python", evaluator=NoOpEvaluator())
    sybil = Sybil(parsers=[parser])
    document = sybil.parse(path=test_file)
    examples = list(document.examples())

    expected_example_count = 2
    assert len(examples) == expected_example_count
    assert examples[0].parsed.text == "x = 1\n"
    assert examples[1].parsed.text == "y = 2\n"


def test_language_filter(tmp_path: Path) -> None:
    """
    Code blocks with a different language are skipped.
    """
    content = """Some text

.. code-block:: python

   x = 1

.. code-block:: bash

   echo "hello"
"""
    test_file = tmp_path / "test.rst"
    test_file.write_text(data=content, encoding="utf-8")

    parser = CodeBlockParser(language="python", evaluator=NoOpEvaluator())
    sybil = Sybil(parsers=[parser])
    document = sybil.parse(path=test_file)
    examples = list(document.examples())

    assert len(examples) == 1
    assert examples[0].parsed.text == "x = 1\n"


def test_no_language_filter(tmp_path: Path) -> None:
    """
    All code blocks are matched when no language filter is specified.
    """
    content = """Some text

.. code-block:: python

   x = 1

.. code-block:: bash

   echo "hello"
"""
    test_file = tmp_path / "test.rst"
    test_file.write_text(data=content, encoding="utf-8")

    parser = CodeBlockParser(evaluator=NoOpEvaluator())
    sybil = Sybil(parsers=[parser])
    document = sybil.parse(path=test_file)
    examples = list(document.examples())

    expected_example_count = 2
    assert len(examples) == expected_example_count


def test_language_lexeme(tmp_path: Path) -> None:
    """
    The language lexeme is set correctly.
    """
    content = """
.. code-block:: python

   x = 1
"""
    test_file = tmp_path / "test.rst"
    test_file.write_text(data=content, encoding="utf-8")

    parser = CodeBlockParser(evaluator=NoOpEvaluator())
    sybil = Sybil(parsers=[parser])
    document = sybil.parse(path=test_file)
    examples = list(document.examples())

    assert len(examples) == 1
    assert examples[0].region.lexemes["language"] == "python"


def test_multiline_code_block(tmp_path: Path) -> None:
    """
    Multiline code blocks are parsed correctly.
    """
    content = """
.. code-block:: python

   def hello():
       print("hello")
       print("world")
"""
    test_file = tmp_path / "test.rst"
    test_file.write_text(data=content, encoding="utf-8")

    parser = CodeBlockParser(language="python", evaluator=NoOpEvaluator())
    sybil = Sybil(parsers=[parser])
    document = sybil.parse(path=test_file)
    examples = list(document.examples())

    assert len(examples) == 1
    expected = 'def hello():\n    print("hello")\n    print("world")\n'
    assert examples[0].parsed.text == expected


def test_evaluator_not_none_when_omitted(tmp_path: Path) -> None:
    """When no evaluator is provided, the region still has an evaluator.

    Sybil's Example.evaluate() does nothing when region.evaluator is
    None. To work correctly with document evaluators (like
    GroupAllParser), the region must have a non-None evaluator. Like
    Sybil's AbstractCodeBlockParser, we provide a default evaluate
    method that raises NotImplementedError.
    """
    content = """
.. code-block:: python

   print('hello')
"""
    test_file = tmp_path / "test.rst"
    test_file.write_text(data=content, encoding="utf-8")

    # Create parser without an evaluator
    parser = CodeBlockParser(language="python")
    sybil = Sybil(parsers=[parser])
    document = sybil.parse(path=test_file)
    examples = list(document.examples())

    assert len(examples) == 1
    # The region should have a non-None evaluator
    assert examples[0].region.evaluator is not None

    # Calling evaluate should raise NotImplementedError (default behavior)
    with pytest.raises(expected_exception=NotImplementedError):
        examples[0].evaluate()
