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


def test_write_to_file_multiple(*, tmp_path: Path) -> None:
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
    file_with_new_content = tmp_path / "new_file.txt"
    # Add multiple newlines to show that they are not included in the file.
    # No code block in reSructuredText ends with multiple newlines.
    new_content = "foobar\n\n"
    file_with_new_content.write_text(data=new_content, encoding="utf-8")

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


"""
TODO:

    # Add multiple newlines to show that they are not included in the file.
    # No code block in reSructuredText ends with multiple newlines.
    new_content = "foobar\n\n"
"""
