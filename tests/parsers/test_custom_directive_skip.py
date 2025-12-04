"""
Custom directive skip parser tests shared across markup languages.
"""

from pathlib import Path

import pytest
from sybil import Sybil
from sybil.evaluators.python import PythonEvaluator
from sybil.evaluators.skip import SkipState

from sybil_extras.languages import MarkupLanguage


def test_skip(language: MarkupLanguage, tmp_path: Path) -> None:
    """
    The custom directive skip parser can be used to set skips.
    """
    content = language.markup_separator.join(
        [
            "Example",
            language.code_block_builder(code="x = []", language="python"),
            language.directive_builder(
                directive="custom-skip", argument="next"
            ),
            language.code_block_builder(code="x = [*x, 2]", language="python"),
            language.code_block_builder(code="x = [*x, 3]", language="python"),
        ]
    )
    test_document = tmp_path / "test"
    test_document.write_text(
        data=f"{content}{language.markup_separator}",
        encoding="utf-8",
    )

    skip_parser = language.skip_parser_cls(directive="custom-skip")
    code_block_parser = language.code_block_parser_cls(
        language="python",
        evaluator=PythonEvaluator(),
    )

    sybil = Sybil(parsers=[code_block_parser, skip_parser])
    document = sybil.parse(path=test_document)
    for example in document.examples():
        example.evaluate()

    assert document.namespace["x"] == [3]

    skip_states: list[SkipState] = []
    skipper = skip_parser.get_skipper()
    for example in document.examples():
        example.evaluate()
        skip_states.append(skipper.state_for(example=example))

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
            remove=False,
            exception=None,
            last_action=None,
        ),
        SkipState(
            active=True,
            remove=False,
            exception=None,
            last_action=None,
        ),
    ]
    assert skip_states == expected_skip_states


def test_directive_name_in_evaluate_error(
    language: MarkupLanguage,
    tmp_path: Path,
) -> None:
    """
    The directive name is included in evaluation errors.
    """
    content = language.directive_builder(
        directive="custom-skip",
        argument="end",
    )
    test_document = tmp_path / "test"
    test_document.write_text(
        data=f"{content}{language.markup_separator}",
        encoding="utf-8",
    )

    skip_parser = language.skip_parser_cls(directive="custom-skip")

    sybil = Sybil(parsers=[skip_parser])
    document = sybil.parse(path=test_document)
    (example,) = document.examples()
    with pytest.raises(
        expected_exception=ValueError,
        match="'custom-skip: end' must follow 'custom-skip: start'",
    ):
        example.evaluate()


def test_directive_name_in_parse_error(
    language: MarkupLanguage,
    tmp_path: Path,
) -> None:
    """
    The directive name is included in parsing errors.
    """
    content = language.directive_builder(
        directive="custom-skip",
        argument="!!!",
    )
    test_document = tmp_path / "test"
    test_document.write_text(
        data=f"{content}{language.markup_separator}",
        encoding="utf-8",
    )

    skip_parser = language.skip_parser_cls(directive="custom-skip")

    sybil = Sybil(parsers=[skip_parser])
    with pytest.raises(
        expected_exception=ValueError,
        match="malformed arguments to custom-skip: '!!!'",
    ):
        sybil.parse(path=test_document)


def test_directive_name_not_regex_escaped(
    language: MarkupLanguage,
    tmp_path: Path,
) -> None:
    """
    Directive names containing regex characters are matched literally.
    """
    directive = "custom-skip[has_square_brackets]"
    content = language.markup_separator.join(
        [
            language.directive_builder(directive=directive, argument="next"),
            language.code_block_builder(code="block = 1", language="python"),
        ]
    )
    test_document = tmp_path / "test"
    test_document.write_text(
        data=f"{content}{language.markup_separator}",
        encoding="utf-8",
    )

    code_block_parser = language.code_block_parser_cls(
        language="python",
        evaluator=PythonEvaluator(),
    )
    skip_parser = language.skip_parser_cls(directive=directive)
    sybil = Sybil(parsers=[code_block_parser, skip_parser])
    document = sybil.parse(path=test_document)
    for example in document.examples():
        example.evaluate()

    assert not document.namespace
