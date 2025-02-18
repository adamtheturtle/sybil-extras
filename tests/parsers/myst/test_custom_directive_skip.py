"""
Tests for the custom directive skip parser for MyST.
"""

from pathlib import Path

import pytest
from sybil import Sybil
from sybil.evaluators.skip import SkipState
from sybil.parsers.myst.codeblock import PythonCodeBlockParser

from sybil_extras.parsers.myst.custom_directive_skip import (
    CustomDirectiveSkipParser,
)


def test_skip(tmp_path: Path) -> None:
    """
    The custom directive skip parser can be used to set skips.
    """
    content = """\
    Example

    ```python
    x = []
    ```

    <!--- custom-skip: next -->

    ```python
    x = [*x, 2]
    ```

    ```python
    x = [*x, 3]
    ```

    % custom-skip: next

    ```python
    x = [*x, 4]
    ```
    """

    test_document = tmp_path / "test.md"
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
        SkipState(
            active=True,
            remove=True,
            exception=None,
            last_action="next",
        ),
        SkipState(active=True, remove=False, exception=None, last_action=None),
    ]
    assert skip_states == expected_skip_states


def test_directive_name_in_error(tmp_path: Path) -> None:
    """
    The custom directive skip parser includes the directive name in errors.
    """
    skip_parser = CustomDirectiveSkipParser(directive="custom-skip")
    content = """\
    <!--- custom-skip: end -->
    """

    test_document = tmp_path / "test.md"
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
