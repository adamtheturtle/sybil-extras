"""Tests for the docutils_rst CodeBlockParser."""

from pathlib import Path
from textwrap import dedent

import pytest
from sybil import Sybil

from sybil_extras.evaluators.no_op import NoOpEvaluator
from sybil_extras.parsers.docutils_rst.codeblock import CodeBlockParser


def test_basic_code_block(tmp_path: Path) -> None:
    """Basic code blocks are parsed correctly."""
    content = dedent(
        text="""\
        Some text

        .. code-block:: python

           print("hello")
    """
    )
    test_file = tmp_path / "test.rst"
    test_file.write_text(data=content, encoding="utf-8")

    parser = CodeBlockParser(language="python", evaluator=NoOpEvaluator())
    sybil = Sybil(parsers=[parser])
    document = sybil.parse(path=test_file)
    examples = list(document.examples())

    assert len(examples) == 1
    assert examples[0].parsed.text == 'print("hello")\n'


def test_multiple_code_blocks(tmp_path: Path) -> None:
    """Multiple code blocks are all parsed."""
    content = dedent(
        text="""\
        Some text

        .. code-block:: python

           x = 1

        More text

        .. code-block:: python

           y = 2
    """
    )
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
    """Code blocks with a different language are skipped."""
    content = dedent(
        text="""\
        Some text

        .. code-block:: python

           x = 1

        .. code-block:: bash

           echo "hello"
    """
    )
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
    All code blocks are matched when no language filter is
    specified.
    """
    content = dedent(
        text="""\
        Some text

        .. code-block:: python

           x = 1

        .. code-block:: bash

           echo "hello"
    """
    )
    test_file = tmp_path / "test.rst"
    test_file.write_text(data=content, encoding="utf-8")

    parser = CodeBlockParser(evaluator=NoOpEvaluator())
    sybil = Sybil(parsers=[parser])
    document = sybil.parse(path=test_file)
    examples = list(document.examples())

    expected_example_count = 2
    assert len(examples) == expected_example_count


def test_language_lexeme(tmp_path: Path) -> None:
    """The language lexeme is set correctly."""
    content = dedent(
        text="""
        .. code-block:: python

           x = 1
    """
    )
    test_file = tmp_path / "test.rst"
    test_file.write_text(data=content, encoding="utf-8")

    parser = CodeBlockParser(evaluator=NoOpEvaluator())
    sybil = Sybil(parsers=[parser])
    document = sybil.parse(path=test_file)
    examples = list(document.examples())

    assert len(examples) == 1
    assert examples[0].region.lexemes["language"] == "python"


def test_multiline_code_block(tmp_path: Path) -> None:
    """Multiline code blocks are parsed correctly."""
    content = dedent(
        text="""
        .. code-block:: python

           def hello():
               print("hello")
               print("world")
    """
    )
    test_file = tmp_path / "test.rst"
    test_file.write_text(data=content, encoding="utf-8")

    parser = CodeBlockParser(language="python", evaluator=NoOpEvaluator())
    sybil = Sybil(parsers=[parser])
    document = sybil.parse(path=test_file)
    examples = list(document.examples())

    assert len(examples) == 1
    expected = 'def hello():\n    print("hello")\n    print("world")\n'
    assert examples[0].parsed.text == expected


def test_literal_block_skipped(tmp_path: Path) -> None:
    """Literal blocks (``::`` syntax) are skipped.

    Docutils literal blocks (created with ``::`` syntax) produce
    ``literal_block`` nodes without the ``code`` class. These should
    not be matched by the parser.
    """
    content = dedent(
        text="""\
        Some text::

           x = 1

        .. code-block:: python

           y = 2
    """
    )
    test_file = tmp_path / "test.rst"
    test_file.write_text(data=content, encoding="utf-8")

    parser = CodeBlockParser(language="python", evaluator=NoOpEvaluator())
    sybil = Sybil(parsers=[parser])
    document = sybil.parse(path=test_file)
    examples = list(document.examples())

    assert len(examples) == 1
    assert examples[0].parsed.text == "y = 2\n"


def test_code_block_without_language(tmp_path: Path) -> None:
    """A code block without a language is matched.

    When ``.. code-block::`` is used without specifying a language,
    the block should be matched when no language filter is set and
    should have an empty language lexeme.
    """
    content = dedent(
        text="""
        .. code-block::

           x = 1
    """
    )
    test_file = tmp_path / "test.rst"
    test_file.write_text(data=content, encoding="utf-8")

    parser = CodeBlockParser(evaluator=NoOpEvaluator())
    sybil = Sybil(parsers=[parser])
    document = sybil.parse(path=test_file)
    examples = list(document.examples())

    assert len(examples) == 1
    assert examples[0].region.lexemes["language"] == ""


def test_content_starting_with_colon(tmp_path: Path) -> None:
    """Content starting with a colon is not mistaken for a directive
    option.

    In RST, directive options (like ``:linenos:``) appear between the
    directive and the blank-line separator. After the blank line,
    everything is content - including lines starting with ``:``.
    """
    content = dedent(
        text="""\
        .. code-block:: yaml

           :key: value
    """
    )
    test_file = tmp_path / "test.rst"
    test_file.write_text(data=content, encoding="utf-8")

    parser = CodeBlockParser(language="yaml", evaluator=NoOpEvaluator())
    sybil = Sybil(parsers=[parser])
    document = sybil.parse(path=test_file)
    examples = list(document.examples())

    assert len(examples) == 1
    assert examples[0].parsed.text == ":key: value\n"


def test_code_directive(tmp_path: Path) -> None:
    """The ``.. code::`` directive is handled like ``.. code-block::``."""
    content = dedent(
        text="""\
        .. code:: python

           print("hello")
    """
    )
    test_file = tmp_path / "test.rst"
    test_file.write_text(data=content, encoding="utf-8")

    parser = CodeBlockParser(language="python", evaluator=NoOpEvaluator())
    sybil = Sybil(parsers=[parser])
    document = sybil.parse(path=test_file)
    examples = list(document.examples())

    assert len(examples) == 1
    assert examples[0].parsed.text == 'print("hello")\n'


def test_code_block_at_end_of_file(tmp_path: Path) -> None:
    """A code block at the end of the file is parsed.

    When a code block is the last content in the file (with no
    trailing content after it), the region end is set to the end
    of the document.
    """
    content = ".. code-block:: python\n\n   x = 1"
    test_file = tmp_path / "test.rst"
    test_file.write_text(data=content, encoding="utf-8")

    parser = CodeBlockParser(language="python", evaluator=NoOpEvaluator())
    sybil = Sybil(parsers=[parser])
    document = sybil.parse(path=test_file)
    examples = list(document.examples())

    assert len(examples) == 1
    assert examples[0].parsed.text == "x = 1\n"


def test_include_directive_does_not_crash(tmp_path: Path) -> None:
    """Files with ``.. include::`` directives are parsed without error.

    When an RST file contains ``.. include::`` with a relative path,
    docutils would normally raise a ``SystemMessage`` (SEVERE/4) because
    the source path is set to ``<sybil>`` and the file cannot be found.
    The parser should handle this gracefully and still parse any code
    blocks in the file.
    """
    content = dedent(
        text="""\
        .. include:: ../../CHANGELOG.rst

        .. code-block:: python

           x = 1
    """
    )
    test_file = tmp_path / "test.rst"
    test_file.write_text(data=content, encoding="utf-8")

    parser = CodeBlockParser(language="python", evaluator=NoOpEvaluator())
    sybil = Sybil(parsers=[parser])
    document = sybil.parse(path=test_file)
    examples = list(document.examples())

    assert len(examples) == 1
    assert examples[0].parsed.text == "x = 1\n"


def test_evaluator_not_none_when_omitted(tmp_path: Path) -> None:
    """When no evaluator is provided, the region still has an evaluator.

    Sybil's Example.evaluate() does nothing when region.evaluator is
    None. To work correctly with document evaluators (like
    GroupAllParser), the region must have a non-None evaluator. Like
    Sybil's AbstractCodeBlockParser, we provide a default evaluate
    method that raises NotImplementedError.
    """
    content = dedent(
        text="""
        .. code-block:: python

           print('hello')
    """
    )
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


def test_invisible_code_block_single_colon(tmp_path: Path) -> None:
    """Single-colon ``invisible-code-block`` directives are parsed.

    ``.. invisible-code-block: python`` (single colon) is an RST
    comment-based directive. The parser should recognize it and extract
    its code content.
    """
    content = dedent(
        text="""\
        Some text

        .. invisible-code-block: python

           x = 1
        """
    )
    test_file = tmp_path / "test.rst"
    test_file.write_text(data=content, encoding="utf-8")

    parser = CodeBlockParser(language="python", evaluator=NoOpEvaluator())
    sybil = Sybil(parsers=[parser])
    document = sybil.parse(path=test_file)
    examples = list(document.examples())

    assert len(examples) == 1
    assert examples[0].parsed.text == "x = 1\n"


def test_invisible_code_block_single_colon_language_filter(
    tmp_path: Path,
) -> None:
    """Single-colon invisible-code-block with wrong language is
    skipped.
    """
    content = dedent(
        text="""\
        .. invisible-code-block: python

           x = 1

        .. invisible-code-block: bash

           echo hello
        """
    )
    test_file = tmp_path / "test.rst"
    test_file.write_text(data=content, encoding="utf-8")

    parser = CodeBlockParser(language="python", evaluator=NoOpEvaluator())
    sybil = Sybil(parsers=[parser])
    document = sybil.parse(path=test_file)
    examples = list(document.examples())

    assert len(examples) == 1
    assert examples[0].parsed.text == "x = 1\n"


def test_invisible_code_block_single_colon_no_language_filter(
    tmp_path: Path,
) -> None:
    """Single-colon invisible-code-block is matched without language
    filter.
    """
    content = dedent(
        text="""\
        .. invisible-code-block: python

           x = 1

        .. invisible-code-block: bash

           echo hello
        """
    )
    test_file = tmp_path / "test.rst"
    test_file.write_text(data=content, encoding="utf-8")

    parser = CodeBlockParser(evaluator=NoOpEvaluator())
    sybil = Sybil(parsers=[parser])
    document = sybil.parse(path=test_file)
    examples = list(document.examples())

    expected_example_count = 2
    assert len(examples) == expected_example_count


def test_invisible_code_block_single_colon_language_lexeme(
    tmp_path: Path,
) -> None:
    """Language lexeme is correct for single-colon invisible-code-
    block.
    """
    content = dedent(
        text="""\
        .. invisible-code-block: python

           x = 1
        """
    )
    test_file = tmp_path / "test.rst"
    test_file.write_text(data=content, encoding="utf-8")

    parser = CodeBlockParser(evaluator=NoOpEvaluator())
    sybil = Sybil(parsers=[parser])
    document = sybil.parse(path=test_file)
    examples = list(document.examples())

    assert len(examples) == 1
    assert examples[0].region.lexemes["language"] == "python"


def test_invisible_code_block_single_colon_and_regular_together(
    tmp_path: Path,
) -> None:
    """Single-colon invisible-code-block and regular code blocks work
    together.
    """
    content = dedent(
        text="""\
        .. code-block:: python

           x = 1

        .. invisible-code-block: python

           y = 2
        """
    )
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


def test_invisible_code_block_single_colon_multiline(tmp_path: Path) -> None:
    """Multiline single-colon invisible-code-block is parsed correctly."""
    content = dedent(
        text="""\
        .. invisible-code-block: python

           def foo():
               pass
        """
    )
    test_file = tmp_path / "test.rst"
    test_file.write_text(data=content, encoding="utf-8")

    parser = CodeBlockParser(language="python", evaluator=NoOpEvaluator())
    sybil = Sybil(parsers=[parser])
    document = sybil.parse(path=test_file)
    examples = list(document.examples())

    assert len(examples) == 1
    assert examples[0].parsed.text == "def foo():\n    pass\n"


def test_invisible_code_block_single_colon_at_end_of_file(
    tmp_path: Path,
) -> None:
    """Single-colon invisible-code-block at end of file is parsed."""
    content = dedent(
        text="""\
        .. invisible-code-block: python

           x = 1"""
    )
    test_file = tmp_path / "test.rst"
    test_file.write_text(data=content, encoding="utf-8")

    parser = CodeBlockParser(language="python", evaluator=NoOpEvaluator())
    sybil = Sybil(parsers=[parser])
    document = sybil.parse(path=test_file)
    examples = list(document.examples())

    assert len(examples) == 1
    assert examples[0].parsed.text == "x = 1\n"


def test_trailing_blank_lines_preserved_in_code_block(
    tmp_path: Path,
) -> None:
    """Trailing blank lines in code block content are preserved.

    When multiple blank lines separate two code blocks, the blank lines
    before the last one are part of the first code block's content. These
    should be preserved in the parsed text to match the behavior of the
    RESTRUCTUREDTEXT parser.
    """
    content = (
        ".. code-block:: python\n"
        "\n"
        "   def my_function() -> None:\n"
        '       """Do nothing."""\n'
        "\n"
        "\n"
        ".. code-block:: python\n"
        "\n"
        "   my_function()\n"
    )
    test_file = tmp_path / "test.rst"
    test_file.write_text(data=content, encoding="utf-8")

    parser = CodeBlockParser(language="python", evaluator=NoOpEvaluator())
    sybil = Sybil(parsers=[parser])
    document = sybil.parse(path=test_file)
    examples = list(document.examples())

    expected_example_count = 2
    assert len(examples) == expected_example_count
    # The trailing blank line between the two code blocks should be
    # preserved as part of the first block's content.
    expected_first = dedent(
        '''\
        def my_function() -> None:
            """Do nothing."""

        '''
    )
    assert examples[0].parsed.text == expected_first
    assert examples[1].parsed.text == "my_function()\n"


def test_trailing_blank_lines_preserved_in_invisible_code_block(
    tmp_path: Path,
) -> None:
    """Trailing blank lines in invisible-code-block content are preserved.

    When multiple blank lines separate two invisible-code-blocks, the blank
    lines before the last one should be preserved in the parsed text.
    """
    content = (
        ".. invisible-code-block: python\n"
        "\n"
        "   def my_function() -> None:\n"
        '       """Do nothing."""\n'
        "\n"
        "\n"
        ".. invisible-code-block: python\n"
        "\n"
        "   my_function()\n"
    )
    test_file = tmp_path / "test.rst"
    test_file.write_text(data=content, encoding="utf-8")

    parser = CodeBlockParser(language="python", evaluator=NoOpEvaluator())
    sybil = Sybil(parsers=[parser])
    document = sybil.parse(path=test_file)
    examples = list(document.examples())

    expected_example_count = 2
    assert len(examples) == expected_example_count
    expected_first = dedent(
        '''\
        def my_function() -> None:
            """Do nothing."""

        '''
    )
    assert examples[0].parsed.text == expected_first
    assert examples[1].parsed.text == "my_function()\n"
