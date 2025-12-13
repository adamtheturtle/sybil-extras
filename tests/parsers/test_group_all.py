"""
Group-all parser tests shared across markup languages.
"""

import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from sybil import Example, Sybil

from sybil_extras.evaluators.block_accumulator import BlockAccumulatorEvaluator
from sybil_extras.evaluators.no_op import NoOpEvaluator
from sybil_extras.evaluators.shell_evaluator import ShellCommandEvaluator
from sybil_extras.languages import (
    MarkupLanguage,
)


def test_group_all(language: MarkupLanguage, tmp_path: Path) -> None:
    """
    All code blocks are grouped into a single block.
    """
    content = language.markup_separator.join(
        [
            language.code_block_builder(code="x = []", language="python"),
            language.code_block_builder(code="x = [*x, 1]", language="python"),
            language.code_block_builder(code="x = [*x, 2]", language="python"),
        ]
    )
    test_document = tmp_path / "test"
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
    separator_newlines = len(language.markup_separator)
    padding_newlines = separator_newlines + 2
    padding = "\n" * padding_newlines
    expected = padding.join(blocks) + "\n"
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
    test_document = tmp_path / "test"
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
    test_document = tmp_path / "test"
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
    content = language.markup_separator.join(
        [
            language.code_block_builder(code="x = []", language="python"),
            language.code_block_builder(code="x = [*x, 1]", language="python"),
            language.code_block_builder(code="x = [*x, 2]", language="python"),
        ]
    )
    test_document = tmp_path / "test"
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
    # When pad_groups=False, blocks are separated by 2 newlines (1 blank line)
    padding = "\n\n"
    expected = padding.join(blocks) + "\n"
    assert document.namespace["blocks"] == [expected]


def test_thread_safety(language: MarkupLanguage, tmp_path: Path) -> None:
    """
    The group-all parser is thread-safe when examples are evaluated
    concurrently.
    """
    content = language.markup_separator.join(
        [
            language.code_block_builder(code="x = [*x, 1]", language="python"),
            language.code_block_builder(code="x = [*x, 2]", language="python"),
            language.code_block_builder(code="x = [*x, 3]", language="python"),
        ]
    )
    test_document = tmp_path / "test"
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

    examples: list[Example] = list(document.examples())

    def evaluate(ex: Example) -> None:
        """
        Evaluate the example.
        """
        ex.evaluate()

    with ThreadPoolExecutor(max_workers=4) as executor:
        list(executor.map(evaluate, examples))

    blocks = ["x = [*x, 1]", "x = [*x, 2]", "x = [*x, 3]"]
    separator_newlines = len(language.markup_separator)
    padding_newlines = separator_newlines + 2
    padding = "\n" * padding_newlines
    expected = padding.join(blocks) + "\n"
    assert document.namespace["blocks"] == [expected]


def test_group_all_with_skip(language: MarkupLanguage, tmp_path: Path) -> None:
    """
    Skip directives are honored when grouping code blocks.
    """
    skip_directive = language.directive_builder(
        directive="skip", argument="next"
    )
    skipped_block = language.code_block_builder(
        code="x = [*x, 1]", language="python"
    )

    content = language.markup_separator.join(
        [
            language.code_block_builder(code="x = []", language="python"),
            skip_directive,
            skipped_block,
            language.code_block_builder(code="x = [*x, 2]", language="python"),
        ]
    )
    test_document = tmp_path / "test"
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

    content_between_blocks = (
        language.markup_separator
        + skip_directive
        + language.markup_separator
        + skipped_block
        + language.markup_separator
    )
    num_newlines_between = content_between_blocks.count("\n")
    skipped_lines = "\n" * (num_newlines_between + 2)
    expected = f"x = []{skipped_lines}x = [*x, 2]\n"
    assert document.namespace["blocks"] == [expected]


def test_evaluation_order_independence(
    language: MarkupLanguage,
    tmp_path: Path,
) -> None:
    """Examples can be evaluated out of order and still produce correct
    results.

    Code blocks are sorted by their position in the document regardless
    of the order in which they are evaluated.
    """
    content = language.markup_separator.join(
        [
            language.code_block_builder(code="x = [1]", language="python"),
            language.code_block_builder(code="x = [*x, 2]", language="python"),
            language.code_block_builder(code="x = [*x, 3]", language="python"),
        ]
    )
    test_document = tmp_path / "test"
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

    examples: list[Example] = list(document.examples())
    # Order: code1, code2, code3, finalize
    code1, code2, code3, finalize = examples

    # Evaluate in a different order: code3, code1, code2, finalize
    code3.evaluate()
    code1.evaluate()
    code2.evaluate()
    finalize.evaluate()

    blocks = ["x = [1]", "x = [*x, 2]", "x = [*x, 3]"]
    separator_newlines = len(language.markup_separator)
    padding_newlines = separator_newlines + 2
    padding = "\n" * padding_newlines
    expected = padding.join(blocks) + "\n"

    # Despite out-of-order evaluation, the result should be sorted by position
    assert document.namespace["blocks"] == [expected]


def test_state_cleanup_on_evaluator_failure(
    language: MarkupLanguage,
    tmp_path: Path,
) -> None:
    """When an evaluator raises an exception, the group-all state is cleaned
    up.

    This ensures that pop_evaluator is called even when the evaluator
    fails, so the document's evaluator stack is properly cleaned up.
    """
    content = language.code_block_builder(code="exit 1", language="bash")
    test_document = tmp_path / "test"
    test_document.write_text(
        data=f"{content}{language.markup_separator}",
        encoding="utf-8",
    )

    shell_evaluator = ShellCommandEvaluator(
        args=["sh"],
        pad_file=False,
        write_to_file=False,
        use_pty=False,
    )
    group_all_parser = language.group_all_parser_cls(
        evaluator=shell_evaluator,
        pad_groups=False,
    )
    code_block_parser = language.code_block_parser_cls(language="bash")

    sybil = Sybil(parsers=[code_block_parser, group_all_parser])
    document = sybil.parse(path=test_document)

    code_block_example, finalize_example = document.examples()

    # Evaluate the code block (gets collected)
    code_block_example.evaluate()

    # Evaluate the finalize marker (will fail due to exit 1)
    with pytest.raises(expected_exception=subprocess.CalledProcessError):
        finalize_example.evaluate()

    # The evaluator should have been popped even though the evaluator failed
    assert len(document.evaluators) == 0


def test_finalize_waits_for_code_blocks(
    language: MarkupLanguage,
    tmp_path: Path,
) -> None:
    """The finalize marker waits for all code blocks to be collected.

    This tests the fix for a race condition where the finalize marker
    could be evaluated before all code blocks were collected, resulting
    in incomplete groups. The finalize marker now waits until all
    expected code blocks have been collected before processing.
    """
    content = language.markup_separator.join(
        [
            language.code_block_builder(code="x = [1]", language="python"),
            language.code_block_builder(code="x = [*x, 2]", language="python"),
        ]
    )
    test_document = tmp_path / "test"
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

    examples: list[Example] = list(document.examples())
    code1, code2, finalize = examples

    # Evaluate finalize marker AND code blocks concurrently.
    # Without the fix, the finalize marker could complete before code blocks
    # are collected, resulting in an empty or partial group.
    # With the fix, the finalize marker waits for all code blocks.
    def evaluate(ex: Example) -> None:
        """
        Evaluate the example.
        """
        ex.evaluate()

    # Run all three concurrently - finalize should wait for code blocks
    with ThreadPoolExecutor(max_workers=3) as executor:
        list(executor.map(evaluate, [finalize, code1, code2]))

    separator_newlines = len(language.markup_separator)
    padding_newlines = separator_newlines + 2
    padding = "\n" * padding_newlines

    # Both code blocks should be in the group, properly combined
    assert document.namespace["blocks"] == [
        f"x = [1]{padding}x = [*x, 2]\n",
    ]
