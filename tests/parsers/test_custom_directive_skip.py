"""
Custom directive skip parser tests shared across markup languages.
"""

from collections.abc import Callable, Iterable
from pathlib import Path

import pytest
from sybil import Document, Region, Sybil
from sybil.evaluators.python import PythonEvaluator
from sybil.evaluators.skip import SkipState

from sybil_extras.languages import MarkupLanguage
from tests.helpers import document_data, join_markup, write_document


def _code_block_parser(
    *,
    language: MarkupLanguage,
) -> Callable[[Document], Iterable[Region]]:
    """
    Instantiate a Python code block parser for ``language``.
    """
    return language.code_block_parser_cls(
        language="python",
        evaluator=PythonEvaluator(),
    )


def test_skip(language: MarkupLanguage, tmp_path: Path) -> None:
    """
    The custom directive skip parser can be used to set skips.
    """
    content = join_markup(
        "Example",
        language.code_block(code="x = []"),
        language.directive(directive="custom-skip", argument="next"),
        language.code_block(code="x = [*x, 2]"),
        language.code_block(code="x = [*x, 3]"),
    )
    test_document = write_document(
        language=language,
        directory=tmp_path,
        data=document_data(language=language, content=content),
    )

    skip_parser = language.skip_parser_cls(directive="custom-skip")
    code_block_parser = _code_block_parser(language=language)

    sybil = Sybil(parsers=[code_block_parser, skip_parser])
    document = sybil.parse(path=test_document)
    for example in document.examples():
        example.evaluate()

    assert document.namespace["x"] == [3]

    skip_states: list[SkipState] = []
    for example in document.examples():
        example.evaluate()
        skip_states.append(skip_parser.skipper.state_for(example=example))

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
    content = language.directive(directive="custom-skip", argument="end")
    test_document = write_document(
        language=language,
        directory=tmp_path,
        data=document_data(language=language, content=content),
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
    content = language.directive(directive="custom-skip", argument="!!!")
    test_document = write_document(
        language=language,
        directory=tmp_path,
        data=document_data(language=language, content=content),
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
    content = join_markup(
        language.directive(directive=directive, argument="next"),
        language.code_block(code="block = 1"),
    )
    test_document = write_document(
        language=language,
        directory=tmp_path,
        data=document_data(language=language, content=content),
    )

    code_block_parser = _code_block_parser(language=language)
    skip_parser = language.skip_parser_cls(directive=directive)
    sybil = Sybil(parsers=[code_block_parser, skip_parser])
    document = sybil.parse(path=test_document)
    for example in document.examples():
        example.evaluate()

    assert not document.namespace
