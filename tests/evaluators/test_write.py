"""
Tests for WriteEvaluator.
"""

import textwrap
from pathlib import Path

import pytest
from sybil import Sybil
from sybil.example import Example
from sybil.parsers.rest.codeblock import CodeBlockParser

from sybil_extras.evaluators.multi import MultiEvaluator
from sybil_extras.evaluators.write import WriteCodeBlockEvaluator


@pytest.fixture(name="rst_file")
def fixture_rst_file(tmp_path: Path) -> Path:
    """
    Fixture to create a temporary RST file with Python code blocks.
    """
    content = """
    .. code-block:: python

        x = 2 + 2
        assert x == 4
    """
    test_document = tmp_path / "test_document.rst"
    test_document.write_text(data=content, encoding="utf-8")
    return test_document


def test_write_to_file_multiple_same(*, tmp_path: Path) -> None:
    """
    If multiple code blocks are present with the same content, changes are
    written to the code block which needs changing.
    """
    content = textwrap.dedent(
        text="""\
        Not in code block

        .. code-block:: python

           x = 2 + 2
           assert x == 4

        .. code-block:: python

           x = 2 + 2
           assert x == 4

        .. code-block:: python

           x = 2 + 2
           assert x == 4
        """
    )
    rst_file = tmp_path / "test_document.example.rst"
    rst_file.write_text(data=content, encoding="utf-8")

    def evaluator(example: Example) -> None:
        """
        Set the parsed text to 'foobar'.
        """
        example.parsed.text = "foobar"

    write_evaluator = WriteCodeBlockEvaluator(
        strip_leading_newlines=True,
        encoding="utf-8",
    )
    multi_evaluator = MultiEvaluator(evaluators=[evaluator, write_evaluator])
    parser = CodeBlockParser(language="python", evaluator=multi_evaluator)
    sybil = Sybil(parsers=[parser])

    document = sybil.parse(path=rst_file)
    (_, second_example, _) = document.examples()
    second_example.evaluate()
    rst_file_content = rst_file.read_text(encoding="utf-8")
    modified_content = textwrap.dedent(
        text="""\
        Not in code block

        .. code-block:: python

           x = 2 + 2
           assert x == 4

        .. code-block:: python

           foobar

        .. code-block:: python

           x = 2 + 2
           assert x == 4
        """,
    )
    assert rst_file_content == modified_content
    assert second_example.document.text == modified_content


def test_write_multiple_to_file(*, tmp_path: Path) -> None:
    """
    Multiple code blocks can be written to the file even if they change the
    length of the contents.
    """
    content = textwrap.dedent(
        text="""\
        Not in code block

        .. code-block:: python

           x = 2 + 2
           assert x == 4

        .. code-block:: python

           x = 2 + 2
           assert x == 4

        .. code-block:: python

           x = 2 + 2
           assert x == 4
        """
    )
    rst_file = tmp_path / "test_document.example.rst"
    rst_file.write_text(data=content, encoding="utf-8")

    def evaluator(example: Example) -> None:
        """
        Set the parsed text to 'foobar'.
        """
        example.parsed.text = "foobar"

    write_evaluator = WriteCodeBlockEvaluator(
        strip_leading_newlines=True,
        encoding="utf-8",
    )
    multi_evaluator = MultiEvaluator(evaluators=[evaluator, write_evaluator])
    parser = CodeBlockParser(language="python", evaluator=multi_evaluator)
    sybil = Sybil(parsers=[parser])

    document = sybil.parse(path=rst_file)
    (first_example, second_example, _) = document.examples()
    second_example.evaluate()
    first_example.evaluate()
    rst_file_content = rst_file.read_text(encoding="utf-8")
    modified_content = textwrap.dedent(
        text="""\
        Not in code block

        .. code-block:: python

           foobar

        .. code-block:: python

           foobar

        .. code-block:: python

           x = 2 + 2
           assert x == 4
        """,
    )
    assert rst_file_content == modified_content
    assert second_example.document.text == modified_content


def test_no_changes_mtime(*, rst_file: Path) -> None:
    """
    The modification time of the file is not changed if no changes are made.
    """
    original_mtime = rst_file.stat().st_mtime

    write_evaluator = WriteCodeBlockEvaluator(
        strip_leading_newlines=True,
        encoding="utf-8",
    )
    parser = CodeBlockParser(language="python", evaluator=write_evaluator)
    sybil = Sybil(parsers=[parser])

    document = sybil.parse(path=rst_file)
    (example,) = document.examples()
    example.evaluate()
    new_mtime = rst_file.stat().st_mtime
    assert new_mtime == original_mtime


def test_empty_code_block_write_to_file(
    *,
    rst_file: Path,
) -> None:
    """
    No error is given with an empty code block.
    """
    content = textwrap.dedent(
        text="""\
        Not in code block

        .. code-block:: python

        After empty code block
        """
    )
    rst_file.write_text(data=content, encoding="utf-8")

    def evaluator(example: Example) -> None:
        """
        Set the parsed text to 'foobar'.
        """
        example.parsed.text = "foobar"

    write_evaluator = WriteCodeBlockEvaluator(
        strip_leading_newlines=True,
        encoding="utf-8",
    )
    multi_evaluator = MultiEvaluator(evaluators=[evaluator, write_evaluator])
    parser = CodeBlockParser(language="python", evaluator=multi_evaluator)
    sybil = Sybil(parsers=[parser])

    document = sybil.parse(path=rst_file)
    (example,) = document.examples()
    example.evaluate()

    rst_file_content = rst_file.read_text(encoding="utf-8")
    modified_content = textwrap.dedent(
        text="""\
        Not in code block

        .. code-block:: python

           foobar

        After empty code block
        """,
    )
    assert rst_file_content == modified_content
