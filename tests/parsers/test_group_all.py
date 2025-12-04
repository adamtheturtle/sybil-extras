"""
Unified tests for the GroupAllParser across markup languages.
"""

from pathlib import Path

import pytest

from sybil_extras.evaluators.block_accumulator import BlockAccumulatorEvaluator
from sybil_extras.evaluators.no_op import NoOpEvaluator

from ._markups import (
    MARKUP_LANGUAGES,
    MarkupLanguage,
    evaluate_document,
    parse_document,
)


@pytest.fixture(params=MARKUP_LANGUAGES, ids=lambda markup: markup.name)
def markup_language(request: pytest.FixtureRequest) -> MarkupLanguage:
    """
    Parameterize tests across markup languages.
    """
    assert isinstance(request.param, MarkupLanguage)
    return request.param


def _make_group_all_parsers(
    markup_language: MarkupLanguage,
    *,
    evaluator: BlockAccumulatorEvaluator,
    pad_groups: bool,
) -> tuple[object, object]:
    """
    Build the common parser instances for the tests.
    """
    group_all_parser = markup_language.group_all_parser_cls(
        evaluator=evaluator,
        pad_groups=pad_groups,
    )
    code_block_parser = markup_language.code_block_parser_cls(
        language="python",
        evaluator=evaluator,
    )
    return code_block_parser, group_all_parser


def test_group_all(markup_language: MarkupLanguage, tmp_path: Path) -> None:
    """
    The group all parser groups all examples in a document.
    """
    evaluator = BlockAccumulatorEvaluator(namespace_key="blocks")
    code_block_parser, group_all_parser = _make_group_all_parsers(
        markup_language=markup_language,
        evaluator=evaluator,
        pad_groups=True,
    )
    document = evaluate_document(
        tmp_path=tmp_path,
        markup=markup_language,
        parts=[
            markup_language.code_block("x = []"),
            markup_language.code_block("x = [*x, 1]"),
            markup_language.code_block("x = [*x, 2]"),
        ],
        parsers=[code_block_parser, group_all_parser],
    )

    expected = markup_language.expected_text(
        "x = []\n\n\n\nx = [*x, 1]\n\n\n\nx = [*x, 2]",
    )
    assert document.namespace["blocks"] == [expected]
    assert len(document.evaluators) == 0


def test_group_all_single_block(
    markup_language: MarkupLanguage,
    tmp_path: Path,
) -> None:
    """
    The group all parser works with a single code block.
    """
    evaluator = BlockAccumulatorEvaluator(namespace_key="blocks")
    code_block_parser, group_all_parser = _make_group_all_parsers(
        markup_language=markup_language,
        evaluator=evaluator,
        pad_groups=True,
    )
    document = evaluate_document(
        tmp_path=tmp_path,
        markup=markup_language,
        parts=[markup_language.code_block("x = []")],
        parsers=[code_block_parser, group_all_parser],
    )

    assert document.namespace["blocks"] == [
        markup_language.expected_text("x = []"),
    ]


def test_group_all_empty_document(
    markup_language: MarkupLanguage,
    tmp_path: Path,
) -> None:
    """
    The group all parser handles an empty document gracefully.
    """
    content = (
        "Empty document\n\nNo code blocks here."
        if markup_language.extension == "rst"
        else "# Empty document\n\nNo code blocks here."
    )
    group_all_parser = markup_language.group_all_parser_cls(
        evaluator=NoOpEvaluator(),
        pad_groups=True,
    )
    code_block_parser = markup_language.code_block_parser_cls(
        language="python"
    )

    document = parse_document(
        tmp_path=tmp_path,
        markup=markup_language,
        parts=[content],
        parsers=[code_block_parser, group_all_parser],
    )
    examples = list(document.examples())
    assert len(examples) == 1
    for example in examples:
        example.evaluate()


def test_group_all_no_pad(
    markup_language: MarkupLanguage, tmp_path: Path
) -> None:
    """
    The group all parser can avoid padding groups.
    """
    evaluator = BlockAccumulatorEvaluator(namespace_key="blocks")
    code_block_parser, group_all_parser = _make_group_all_parsers(
        markup_language=markup_language,
        evaluator=evaluator,
        pad_groups=False,
    )
    document = evaluate_document(
        tmp_path=tmp_path,
        markup=markup_language,
        parts=[
            markup_language.code_block("x = []"),
            markup_language.code_block("x = [*x, 1]"),
            markup_language.code_block("x = [*x, 2]"),
        ],
        parsers=[code_block_parser, group_all_parser],
    )

    expected = markup_language.expected_text(
        "x = []\n\nx = [*x, 1]\n\nx = [*x, 2]",
    )
    assert document.namespace["blocks"] == [expected]


def test_group_all_with_skip(
    markup_language: MarkupLanguage,
    tmp_path: Path,
) -> None:
    """
    The group all parser works with skip directives.
    """
    evaluator = BlockAccumulatorEvaluator(namespace_key="blocks")
    code_block_parser, group_all_parser = _make_group_all_parsers(
        markup_language=markup_language,
        evaluator=evaluator,
        pad_groups=True,
    )
    skip_parser = markup_language.skip_parser_cls()

    document = evaluate_document(
        tmp_path=tmp_path,
        markup=markup_language,
        parts=[
            markup_language.code_block("x = []"),
            markup_language.directive("skip: next"),
            markup_language.code_block("x = [*x, 1]"),
            markup_language.code_block("x = [*x, 2]"),
        ],
        parsers=[code_block_parser, skip_parser, group_all_parser],
    )

    expected = markup_language.expected_text(
        "x = []\n\n\n\n\n\n\n\n\n\nx = [*x, 2]",
    )
    assert document.namespace["blocks"] == [expected]
