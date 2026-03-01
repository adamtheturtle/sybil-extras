"""Tests for the docutils_rst lexers."""

from pathlib import Path
from textwrap import dedent

from sybil import Sybil
from sybil.evaluators.python import PythonEvaluator

from sybil_extras.parsers.docutils_rst.codeblock import CodeBlockParser
from sybil_extras.parsers.docutils_rst.custom_directive_skip import (
    CustomDirectiveSkipParser,
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


def test_include_directive_does_not_crash(tmp_path: Path) -> None:
    """Files with ``.. include::`` directives are parsed without error.

    When an RST file contains ``.. include::`` with a relative path,
    docutils would normally raise a ``SystemMessage`` (SEVERE/4) because
    the source path is set to ``<sybil>`` and the file cannot be found.
    The lexer should handle this gracefully and still find directives
    in comments in the file.
    """
    content = dedent(
        text="""\
        .. include:: ../../CHANGELOG.rst

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

    for example in document.examples():
        example.evaluate()

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
