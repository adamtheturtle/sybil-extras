"""Tests for the docutils_rst lexers."""

from pathlib import Path
from textwrap import dedent

import pytest
from docutils import nodes
from sybil import Document, Sybil
from sybil.evaluators.python import PythonEvaluator

from sybil_extras.parsers.docutils_rst._line_offsets import line_offsets
from sybil_extras.parsers.docutils_rst.codeblock import CodeBlockParser
from sybil_extras.parsers.docutils_rst.custom_directive_skip import (
    CustomDirectiveSkipParser,
)
from sybil_extras.parsers.docutils_rst.lexers import (
    DirectiveInCommentLexer,
)


def test_directive_in_comment(tmp_path: Path) -> None:
    """Directive in an RST comment is recognized."""
    content = dedent(
        text="""
        .. custom-skip: next

        .. code-block:: python

           x = 1
    """
    )
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
    """Directive without a colon is also recognized."""
    content = dedent(
        text="""
        .. custom-skip next

        .. code-block:: python

           x = 1
    """
    )
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


def test_directive_at_end_of_file(tmp_path: Path) -> None:
    """A directive comment at the end of the file is recognized.

    When the comment is the last content in the file, the region end
    is set to the end of the document text.
    """
    content = ".. code-block:: python\n\n   x = 1\n\n.. custom-skip: next"
    test_file = tmp_path / "test.rst"
    test_file.write_text(data=content, encoding="utf-8")

    skip_parser = CustomDirectiveSkipParser(directive="custom-skip")
    code_parser = CodeBlockParser(
        language="python",
        evaluator=PythonEvaluator(),
    )
    sybil = Sybil(parsers=[code_parser, skip_parser])
    document = sybil.parse(path=test_file)

    examples = list(document.examples())
    expected_example_count = 2
    assert len(examples) == expected_example_count


def test_process_comment_node_no_line_number() -> None:
    """Raises ValueError when a comment node has no line number."""
    text = ".. custom-skip: next\n"
    document = Document(text=text, path="test.rst")
    offsets = line_offsets(text=text)

    node = nodes.comment(text="custom-skip: next")
    # Do not set node.line

    lexer = DirectiveInCommentLexer(directive="custom-skip")
    with pytest.raises(expected_exception=ValueError, match="no line"):
        lexer._process_comment_node(  # noqa: SLF001  # pyright: ignore[reportPrivateUsage]
            node=node,
            document=document,
            offsets=offsets,
        )


def test_process_comment_node_line_out_of_range() -> None:
    """Raises ValueError when a comment line number is out of range."""
    text = ".. custom-skip: next\n"
    document = Document(text=text, path="test.rst")
    offsets = line_offsets(text=text)

    node = nodes.comment(text="custom-skip: next")
    node.line = 999

    lexer = DirectiveInCommentLexer(directive="custom-skip")
    with pytest.raises(expected_exception=ValueError, match="beyond"):
        lexer._process_comment_node(  # noqa: SLF001  # pyright: ignore[reportPrivateUsage]
            node=node,
            document=document,
            offsets=offsets,
        )
