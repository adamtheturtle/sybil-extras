"""
Group-all parser tests shared across markup languages.
"""

from collections.abc import Callable, Iterable
from pathlib import Path

from sybil import Document, Region, Sybil
from sybil.typing import Evaluator

from sybil_extras.evaluators.block_accumulator import BlockAccumulatorEvaluator
from sybil_extras.evaluators.no_op import NoOpEvaluator
from sybil_extras.languages import (
    MarkupLanguage,
)
from tests.helpers import join_markup, write_document


def _code_block_parser(
    *,
    language: MarkupLanguage,
    evaluator: Evaluator | None,
) -> Callable[[Document], Iterable[Region]]:
    """
    Instantiate a Python code block parser for ``language``.
    """
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

    # Skip directives (and the skipped block) span ten lines, so pad with the
    # same number of newlines to keep downstream line numbers aligned.
    skipped_lines = "\n" * 10
    expected = f"x = []{skipped_lines}x = [*x, 2]\n"
    assert document.namespace["blocks"] == [expected]
