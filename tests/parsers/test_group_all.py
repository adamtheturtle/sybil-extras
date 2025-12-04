"""
Group-all parser tests shared across markup languages.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from sybil import Document, Region, Sybil

from sybil_extras.evaluators.block_accumulator import BlockAccumulatorEvaluator
from sybil_extras.evaluators.no_op import NoOpEvaluator
from sybil_extras.languages import (
    ALL_LANGUAGES,
    RESTRUCTUREDTEXT,
    MarkupLanguage,
)
from tests.helpers import join_markup, write_document

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable
    from pathlib import Path

    from sybil.typing import Evaluator

_PAD_SEPARATOR = "\n\n\n\n"
_NO_PAD_SEPARATOR = "\n\n"
_SKIP_GAP = "\n" * 10


@pytest.fixture(name="language", params=ALL_LANGUAGES)
def fixture_language(request: pytest.FixtureRequest) -> MarkupLanguage:
    """
    Provide each supported markup language for parametrized tests.
    """
    language = request.param
    assert isinstance(language, MarkupLanguage)
    return language


def _code_block_parser(
    *,
    language: MarkupLanguage,
    evaluator: Evaluator | None,
) -> Callable[[Document], Iterable[Region]]:
    """
    Instantiate a Python code block parser for ``language``.
    """
    if evaluator is None:
        return language.code_block_parser_cls(language="python")
    return language.code_block_parser_cls(
        language="python",
        evaluator=evaluator,
    )


def _group_all_parser(
    *,
    language: MarkupLanguage,
    evaluator: Evaluator,
    pad_groups: bool,
) -> Callable[[Document], Iterable[Region]]:
    """
    Instantiate a group-all parser for ``language``.
    """
    return language.group_all_parser_cls(
        evaluator=evaluator,
        pad_groups=pad_groups,
    )


def _expected_padded(language: MarkupLanguage, blocks: list[str]) -> str:
    """
    Return the expected padded representation for ``blocks``.
    """
    result = _PAD_SEPARATOR.join(blocks)
    if language is not RESTRUCTUREDTEXT:
        result += "\n"
    return result


def _expected_no_pad(language: MarkupLanguage, blocks: list[str]) -> str:
    """
    Return the expected unpadded representation for ``blocks``.
    """
    result = _NO_PAD_SEPARATOR.join(blocks)
    if language is not RESTRUCTUREDTEXT:
        result += "\n"
    return result


def _expected_skip(language: MarkupLanguage) -> str:
    """
    Return the expected representation when a block is skipped.
    """
    result = f"x = []{_SKIP_GAP}x = [*x, 2]"
    if language is not RESTRUCTUREDTEXT:
        result += "\n"
    return result


def test_group_all(language: MarkupLanguage, tmp_path: Path) -> None:
    """
    All code blocks are grouped into a single block.
    """
    content = join_markup(
        language.code_block(code="x = []"),
        language.code_block(code="x = [*x, 1]"),
        language.code_block(code="x = [*x, 2]"),
    )
    test_document = write_document(
        language=language,
        directory=tmp_path,
        content=content,
    )

    evaluator = BlockAccumulatorEvaluator(namespace_key="blocks")
    group_all_parser = _group_all_parser(
        language=language,
        evaluator=evaluator,
        pad_groups=True,
    )
    code_block_parser = _code_block_parser(
        language=language,
        evaluator=evaluator,
    )

    sybil = Sybil(parsers=[code_block_parser, group_all_parser])
    document = sybil.parse(path=test_document)

    for example in document.examples():
        example.evaluate()

    expected = _expected_padded(
        language=language,
        blocks=["x = []", "x = [*x, 1]", "x = [*x, 2]"],
    )
    assert document.namespace["blocks"] == [expected]
    assert len(document.evaluators) == 0


def test_group_all_single_block(
    language: MarkupLanguage,
    tmp_path: Path,
) -> None:
    """
    Grouping a single block preserves it.
    """
    content = language.code_block(code="x = []")
    test_document = write_document(
        language=language,
        directory=tmp_path,
        content=content,
    )

    evaluator = BlockAccumulatorEvaluator(namespace_key="blocks")
    group_all_parser = _group_all_parser(
        language=language,
        evaluator=evaluator,
        pad_groups=True,
    )
    code_block_parser = _code_block_parser(
        language=language,
        evaluator=evaluator,
    )

    sybil = Sybil(parsers=[code_block_parser, group_all_parser])
    document = sybil.parse(path=test_document)

    for example in document.examples():
        example.evaluate()

    expected = _expected_padded(language=language, blocks=["x = []"])
    assert document.namespace["blocks"] == [expected]


def test_group_all_empty_document(
    language: MarkupLanguage,
    tmp_path: Path,
) -> None:
    """
    Empty documents do not raise errors.
    """
    content = "Empty document without code blocks."
    test_document = write_document(
        language=language,
        directory=tmp_path,
        content=content,
    )

    group_all_parser = _group_all_parser(
        language=language,
        evaluator=NoOpEvaluator(),
        pad_groups=True,
    )
    code_block_parser = _code_block_parser(
        language=language,
        evaluator=None,
    )

    sybil = Sybil(parsers=[code_block_parser, group_all_parser])
    document = sybil.parse(path=test_document)

    examples = list(document.examples())
    assert len(examples) == 1
    for example in examples:
        example.evaluate()


def test_group_all_no_pad(language: MarkupLanguage, tmp_path: Path) -> None:
    """
    Groups can be combined without inserting extra padding.
    """
    content = join_markup(
        language.code_block(code="x = []"),
        language.code_block(code="x = [*x, 1]"),
        language.code_block(code="x = [*x, 2]"),
    )
    test_document = write_document(
        language=language,
        directory=tmp_path,
        content=content,
    )

    evaluator = BlockAccumulatorEvaluator(namespace_key="blocks")
    group_all_parser = _group_all_parser(
        language=language,
        evaluator=evaluator,
        pad_groups=False,
    )
    code_block_parser = _code_block_parser(
        language=language,
        evaluator=evaluator,
    )

    sybil = Sybil(parsers=[code_block_parser, group_all_parser])
    document = sybil.parse(path=test_document)

    for example in document.examples():
        example.evaluate()

    expected = _expected_no_pad(
        language=language,
        blocks=["x = []", "x = [*x, 1]", "x = [*x, 2]"],
    )
    assert document.namespace["blocks"] == [expected]


def test_group_all_with_skip(language: MarkupLanguage, tmp_path: Path) -> None:
    """
    Skip directives are honored when grouping code blocks.
    """
    content = join_markup(
        language.code_block(code="x = []"),
        language.directive(directive="skip", argument="next"),
        language.code_block(code="x = [*x, 1]"),
        language.code_block(code="x = [*x, 2]"),
    )
    test_document = write_document(
        language=language,
        directory=tmp_path,
        content=content,
    )

    evaluator = BlockAccumulatorEvaluator(namespace_key="blocks")
    group_all_parser = _group_all_parser(
        language=language,
        evaluator=evaluator,
        pad_groups=True,
    )
    code_block_parser = _code_block_parser(
        language=language,
        evaluator=evaluator,
    )
    skip_parser = language.skip_parser_cls(directive="skip")

    sybil = Sybil(parsers=[code_block_parser, skip_parser, group_all_parser])
    document = sybil.parse(path=test_document)

    for example in document.examples():
        example.evaluate()

    expected = _expected_skip(language=language)
    assert document.namespace["blocks"] == [expected]
