"""
Group-all parser tests shared across markup languages.
"""

from pathlib import Path

from sybil import Sybil

from sybil_extras.evaluators.block_accumulator import BlockAccumulatorEvaluator
from sybil_extras.evaluators.no_op import NoOpEvaluator
from sybil_extras.languages import (
    MarkupLanguage,
)
from tests.helpers import join_markup


def test_group_all(language: MarkupLanguage, tmp_path: Path) -> None:
    """
    All code blocks are grouped into a single block.
    """
    content = join_markup(
        language.code_block_builder(code="x = []", language="python"),
        language.code_block_builder(code="x = [*x, 1]", language="python"),
        language.code_block_builder(code="x = [*x, 2]", language="python"),
    )
    test_document = tmp_path / f"test{language.file_extension}"
    test_document.write_text(
        data=f"{content}{language.markup_separator}",
        encoding="utf-8",
    )

    evaluator = BlockAccumulatorEvaluator(namespace_key="blocks")
    group_all_parser = language.group_all_parser_cls(
        evaluator=evaluator,
        pad_groups=True,
    )
    code_block_parser = language.code_block_parser_cls(
        language="python",
        evaluator=evaluator,
    )

    sybil = Sybil(parsers=[code_block_parser, group_all_parser])
    document = sybil.parse(path=test_document)

    for example in document.examples():
        example.evaluate()

    blocks = ["x = []", "x = [*x, 1]", "x = [*x, 2]"]
    # join_markup inserts one blank line (``\n\n``) between fragments; padding
    # duplicates that blank line so line numbers stay aligned with the source.
    separator = "\n\n" * 2
    expected = separator.join(blocks) + "\n"
    assert document.namespace["blocks"] == [expected]
    assert len(document.evaluators) == 0


def test_group_all_single_block(
    language: MarkupLanguage,
    tmp_path: Path,
) -> None:
    """
    Grouping a single block preserves it.
    """
    content = language.code_block_builder(code="x = []", language="python")
    test_document = tmp_path / f"test{language.file_extension}"
    test_document.write_text(
        data=f"{content}{language.markup_separator}",
        encoding="utf-8",
    )

    evaluator = BlockAccumulatorEvaluator(namespace_key="blocks")
    group_all_parser = language.group_all_parser_cls(
        evaluator=evaluator,
        pad_groups=True,
    )
    code_block_parser = language.code_block_parser_cls(
        language="python",
        evaluator=evaluator,
    )

    sybil = Sybil(parsers=[code_block_parser, group_all_parser])
    document = sybil.parse(path=test_document)

    for example in document.examples():
        example.evaluate()

    expected = "x = []\n"
    assert document.namespace["blocks"] == [expected]


def test_group_all_empty_document(
    language: MarkupLanguage,
    tmp_path: Path,
) -> None:
    """
    Empty documents do not raise errors.
    """
    content = "Empty document without code blocks."
    test_document = tmp_path / f"test{language.file_extension}"
    test_document.write_text(
        data=f"{content}{language.markup_separator}",
        encoding="utf-8",
    )

    group_all_parser = language.group_all_parser_cls(
        evaluator=NoOpEvaluator(),
        pad_groups=True,
    )
    code_block_parser = language.code_block_parser_cls(
        language="python",
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
        language.code_block_builder(code="x = []", language="python"),
        language.code_block_builder(code="x = [*x, 1]", language="python"),
        language.code_block_builder(code="x = [*x, 2]", language="python"),
    )
    test_document = tmp_path / f"test{language.file_extension}"
    test_document.write_text(
        data=f"{content}{language.markup_separator}",
        encoding="utf-8",
    )

    evaluator = BlockAccumulatorEvaluator(namespace_key="blocks")
    group_all_parser = language.group_all_parser_cls(
        evaluator=evaluator,
        pad_groups=False,
    )
    code_block_parser = language.code_block_parser_cls(
        language="python",
        evaluator=evaluator,
    )

    sybil = Sybil(parsers=[code_block_parser, group_all_parser])
    document = sybil.parse(path=test_document)

    for example in document.examples():
        example.evaluate()

    blocks = ["x = []", "x = [*x, 1]", "x = [*x, 2]"]
    # Groups are concatenated directly with the blank line produced by
    # ``join_markup``.
    expected = "\n\n".join(blocks) + "\n"
    assert document.namespace["blocks"] == [expected]


def test_group_all_with_skip(language: MarkupLanguage, tmp_path: Path) -> None:
    """
    Skip directives are honored when grouping code blocks.
    """
    content = join_markup(
        language.code_block_builder(code="x = []", language="python"),
        language.directive_builder(directive="skip", argument="next"),
        language.code_block_builder(code="x = [*x, 1]", language="python"),
        language.code_block_builder(code="x = [*x, 2]", language="python"),
    )
    test_document = tmp_path / f"test{language.file_extension}"
    test_document.write_text(
        data=f"{content}{language.markup_separator}",
        encoding="utf-8",
    )

    evaluator = BlockAccumulatorEvaluator(namespace_key="blocks")
    group_all_parser = language.group_all_parser_cls(
        evaluator=evaluator,
        pad_groups=True,
    )
    code_block_parser = language.code_block_parser_cls(
        language="python",
        evaluator=evaluator,
    )
    skip_parser = language.skip_parser_cls(directive="skip")

    sybil = Sybil(parsers=[code_block_parser, skip_parser, group_all_parser])
    document = sybil.parse(path=test_document)

    for example in document.examples():
        example.evaluate()

    # Skip directives (and the skipped block) span ten lines, so pad with the
    # same number of newlines to keep downstream line numbers aligned.
    skipped_lines = "\n" * 10
    expected = f"x = []{skipped_lines}x = [*x, 2]\n"
    assert document.namespace["blocks"] == [expected]
