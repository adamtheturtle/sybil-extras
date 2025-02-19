"""
Tests for the custom directive skip parser for reST.
"""

from pathlib import Path

import pytest
from sybil import Sybil
from sybil.evaluators.skip import SkipState
from sybil.parsers.rest.codeblock import PythonCodeBlockParser

from sybil_extras.parsers.rest.custom_directive_skip import (
    CustomDirectiveSkipParser,
)


def test_skip(tmp_path: Path) -> None:
    """
    The custom directive skip parser can be used to set skips.
    """
    content = """\

    .. code-block:: python

        x = []

    .. custom-skip: next

    .. code-block:: python

        x = [*x, 2]

    .. code-block:: python

        x = [*x, 3]
    """

    test_document = tmp_path / "test.rst"
    test_document.write_text(data=content, encoding="utf-8")

    skip_parser = CustomDirectiveSkipParser(directive="custom-skip")
    code_block_parser = PythonCodeBlockParser()

    sybil = Sybil(parsers=[code_block_parser, skip_parser])
    document = sybil.parse(path=test_document)
    skip_states: list[SkipState] = []
    for example in document.examples():
        example.evaluate()
        skip_states.append(skip_parser.skipper.state_for(example=example))

    assert document.namespace["x"] == [3]
    expected_skip_states = [
        SkipState(
            active=True,
            remove=True,
            exception=None,
            last_action="next",
        ),
        SkipState(
            active=True,
            remove=True,
            exception=None,
            last_action="next",
        ),
        SkipState(active=True, remove=False, exception=None, last_action=None),
        SkipState(active=True, remove=False, exception=None, last_action=None),
    ]
    assert skip_states == expected_skip_states


def test_directive_name_in_evaluate_error(tmp_path: Path) -> None:
    """
    The custom directive skip parser includes the directive name in evaluation
    errors.
    """
    skip_parser = CustomDirectiveSkipParser(directive="custom-skip")
    content = """\
    .. custom-skip: end
    """

    test_document = tmp_path / "test.rst"
    test_document.write_text(data=content, encoding="utf-8")

    skip_parser = CustomDirectiveSkipParser(directive="custom-skip")

    sybil = Sybil(parsers=[skip_parser])
    document = sybil.parse(path=test_document)
    (example,) = document.examples()
    with pytest.raises(
        expected_exception=ValueError,
        match="'custom-skip: end' must follow 'custom-skip: start'",
    ):
        example.evaluate()


def test_directive_name_in_parse_error(tmp_path: Path) -> None:
    """
    The custom directive skip parser includes the directive name in parsing
    errors.
    """
    skip_parser = CustomDirectiveSkipParser(directive="custom-skip")
    content = """\
    .. custom-skip: !!!
    """

    test_document = tmp_path / "test.rst"
    test_document.write_text(data=content, encoding="utf-8")

    skip_parser = CustomDirectiveSkipParser(directive="custom-skip")

    sybil = Sybil(parsers=[skip_parser])
    with pytest.raises(
        expected_exception=ValueError,
        match="malformed arguments to custom-skip: '!!!'",
    ):
        sybil.parse(path=test_document)


def test_directive_name_not_regex_escaped(tmp_path: Path) -> None:
    """
    If the directive name is not regex-escaped, it is still matched.
    """
    content = """\
    .. custom-skip[has_square_brackets]: next

    .. code-block:: python

        block = 1
    """

    test_document = tmp_path / "test.md"
    test_document.write_text(data=content, encoding="utf-8")

    code_block_parser = PythonCodeBlockParser()
    skip_parser = CustomDirectiveSkipParser(
        directive="custom-skip[has_square_brackets]",
    )
    sybil = Sybil(parsers=[code_block_parser, skip_parser])
    document = sybil.parse(path=test_document)
    for example in document.examples():
        example.evaluate()

    assert not document.namespace
