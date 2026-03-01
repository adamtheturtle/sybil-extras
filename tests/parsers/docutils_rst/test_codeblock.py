"""Tests for the docutils_rst CodeBlockParser."""

from pathlib import Path
from textwrap import dedent

import pytest
from docutils import nodes
from sybil import Document, Sybil

from sybil_extras.evaluators.no_op import NoOpEvaluator
from sybil_extras.parsers.docutils_rst._line_offsets import line_offsets
from sybil_extras.parsers.docutils_rst.codeblock import (
    CodeBlockParser,
    _compute_positions,  # pyright: ignore[reportPrivateUsage]
    _find_content_after_directive,  # pyright: ignore[reportPrivateUsage]
    _find_directive_before_content,  # pyright: ignore[reportPrivateUsage]
)


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


def test_compute_positions_ref_line_too_low() -> None:
    """A ref_line below 1 raises ValueError."""
    with pytest.raises(expected_exception=ValueError, match="out of range"):
        _compute_positions(
            lines=[".. code-block:: python", "", "   x = 1"],
            ref_line=0,
            line_count=1,
            language="python",
        )


def test_compute_positions_ref_line_too_high() -> None:
    """A ref_line beyond the number of lines raises ValueError."""
    with pytest.raises(expected_exception=ValueError, match="out of range"):
        _compute_positions(
            lines=[".. code-block:: python", "", "   x = 1"],
            ref_line=99,
            line_count=1,
            language="python",
        )


def test_find_content_after_directive_no_content() -> None:
    """Raises ValueError when there is no content after the directive."""
    with pytest.raises(expected_exception=ValueError, match="No content"):
        _find_content_after_directive(
            lines=[".. code-block:: python", ""],
            directive_line=1,
        )


def test_find_directive_before_content_no_directive() -> None:
    """Raises ValueError when no directive is found before the content."""
    with pytest.raises(expected_exception=ValueError, match="No directive"):
        _find_directive_before_content(
            lines=["x = 1"],
            content_start_line=1,
            language="python",
        )


def test_find_directive_before_content_other_content() -> None:
    """Raises ValueError when non-directive content is hit."""
    with pytest.raises(expected_exception=ValueError, match="No directive"):
        _find_directive_before_content(
            lines=["Some other text", "   x = 1"],
            content_start_line=2,
            language="python",
        )


def test_process_node_no_line_reference() -> None:
    """Raises ValueError when a code block node has no line reference."""
    text = ".. code-block:: python\n\n   x = 1\n"
    document = Document(text=text, path="test.rst")
    offsets = line_offsets(text=text)
    lines_list = text.split(sep="\n")

    node = nodes.literal_block(rawsource="x = 1", text="x = 1")
    node["classes"] = ["code", "python"]
    # Do not set node.line or node.parent

    parser = CodeBlockParser(language="python", evaluator=NoOpEvaluator())
    with pytest.raises(expected_exception=ValueError, match="no line"):
        parser._process_node(  # noqa: SLF001  # pyright: ignore[reportPrivateUsage]
            node=node,
            document=document,
            offsets=offsets,
            lines=lines_list,
        )
