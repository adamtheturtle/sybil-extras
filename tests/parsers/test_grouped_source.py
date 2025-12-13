"""
Grouped source parser tests shared across markup languages.
"""

import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from sybil import Example, Sybil

from sybil_extras.evaluators.block_accumulator import BlockAccumulatorEvaluator
from sybil_extras.evaluators.no_op import NoOpEvaluator
from sybil_extras.evaluators.shell_evaluator import ShellCommandEvaluator
from sybil_extras.languages import MarkupLanguage


def test_group(language: MarkupLanguage, tmp_path: Path) -> None:
    """
    The group parser groups examples.
    """
    content = language.markup_separator.join(
        [
            language.code_block_builder(code="x = []", language="python"),
            language.directive_builder(directive="group", argument="start"),
            language.code_block_builder(code="x = [*x, 1]", language="python"),
            language.code_block_builder(code="x = [*x, 2]", language="python"),
            language.directive_builder(directive="group", argument="end"),
            language.code_block_builder(code="x = [*x, 3]", language="python"),
            language.directive_builder(directive="group", argument="start"),
            language.code_block_builder(code="x = [*x, 4]", language="python"),
            language.code_block_builder(code="x = [*x, 5]", language="python"),
            language.directive_builder(directive="group", argument="end"),
        ]
    )
    test_document = tmp_path / "test"
    test_document.write_text(
        data=f"{content}{language.markup_separator}",
        encoding="utf-8",
    )

    evaluator = BlockAccumulatorEvaluator(namespace_key="blocks")
    group_parser = language.group_parser_cls(
        directive="group",
        evaluator=evaluator,
        pad_groups=True,
    )
    code_block_parser = language.code_block_parser_cls(
        language="python",
        evaluator=evaluator,
    )

    sybil = Sybil(parsers=[code_block_parser, group_parser])
    document = sybil.parse(path=test_document)

    for example in document.examples():
        example.evaluate()

    separator_newlines = len(language.markup_separator)
    padding_newlines = separator_newlines + 1
    padding = "\n" * padding_newlines

    assert document.namespace["blocks"] == [
        "x = []\n",
        f"x = [*x, 1]\n{padding}x = [*x, 2]\n",
        "x = [*x, 3]\n",
        f"x = [*x, 4]\n{padding}x = [*x, 5]\n",
    ]


def test_nothing_after_group(language: MarkupLanguage, tmp_path: Path) -> None:
    """
    Groups are handled even at the end of a document.
    """
    content = language.markup_separator.join(
        [
            language.code_block_builder(code="x = []", language="python"),
            language.directive_builder(directive="group", argument="start"),
            language.code_block_builder(code="x = [*x, 1]", language="python"),
            language.code_block_builder(code="x = [*x, 2]", language="python"),
            language.directive_builder(directive="group", argument="end"),
        ]
    )
    test_document = tmp_path / "test"
    test_document.write_text(
        data=f"{content}{language.markup_separator}",
        encoding="utf-8",
    )

    evaluator = BlockAccumulatorEvaluator(namespace_key="blocks")
    group_parser = language.group_parser_cls(
        directive="group",
        evaluator=evaluator,
        pad_groups=True,
    )
    code_block_parser = language.code_block_parser_cls(
        language="python",
        evaluator=evaluator,
    )

    sybil = Sybil(parsers=[code_block_parser, group_parser])
    document = sybil.parse(path=test_document)

    for example in document.examples():
        example.evaluate()

    separator_newlines = len(language.markup_separator)
    padding_newlines = separator_newlines + 1
    padding = "\n" * padding_newlines

    assert document.namespace["blocks"] == [
        "x = []\n",
        f"x = [*x, 1]\n{padding}x = [*x, 2]\n",
    ]


def test_empty_group(language: MarkupLanguage, tmp_path: Path) -> None:
    """
    Empty groups are handled gracefully.
    """
    content = language.markup_separator.join(
        [
            language.code_block_builder(code="x = []", language="python"),
            language.directive_builder(directive="group", argument="start"),
            language.directive_builder(directive="group", argument="end"),
            language.code_block_builder(code="x = [*x, 3]", language="python"),
        ]
    )
    test_document = tmp_path / "test"
    test_document.write_text(
        data=f"{content}{language.markup_separator}",
        encoding="utf-8",
    )

    evaluator = BlockAccumulatorEvaluator(namespace_key="blocks")
    group_parser = language.group_parser_cls(
        directive="group",
        evaluator=evaluator,
        pad_groups=True,
    )
    code_block_parser = language.code_block_parser_cls(
        language="python",
        evaluator=evaluator,
    )

    sybil = Sybil(parsers=[code_block_parser, group_parser])
    document = sybil.parse(path=test_document)

    for example in document.examples():
        example.evaluate()

    assert document.namespace["blocks"] == [
        "x = []\n",
        "x = [*x, 3]\n",
    ]


def test_group_with_skip(language: MarkupLanguage, tmp_path: Path) -> None:
    """
    Skip directives are respected within a group.
    """
    content = language.markup_separator.join(
        [
            language.code_block_builder(code="x = []", language="python"),
            language.directive_builder(directive="group", argument="start"),
            language.code_block_builder(code="x = [*x, 1]", language="python"),
            language.directive_builder(directive="skip", argument="next"),
            language.code_block_builder(code="x = [*x, 2]", language="python"),
            language.directive_builder(directive="group", argument="end"),
            language.code_block_builder(code="x = [*x, 3]", language="python"),
        ]
    )
    test_document = tmp_path / "test"
    test_document.write_text(
        data=f"{content}{language.markup_separator}",
        encoding="utf-8",
    )

    evaluator = BlockAccumulatorEvaluator(namespace_key="blocks")
    group_parser = language.group_parser_cls(
        directive="group",
        evaluator=evaluator,
        pad_groups=True,
    )
    code_block_parser = language.code_block_parser_cls(
        language="python",
        evaluator=evaluator,
    )
    skip_parser = language.skip_parser_cls(directive="skip")

    sybil = Sybil(parsers=[code_block_parser, skip_parser, group_parser])
    document = sybil.parse(path=test_document)

    for example in document.examples():
        example.evaluate()

    assert document.namespace["blocks"] == [
        "x = []\n",
        "x = [*x, 1]\n",
        "x = [*x, 3]\n",
    ]


def test_group_with_skip_range(
    language: MarkupLanguage, tmp_path: Path
) -> None:
    """
    Skip start/end ranges are respected within a group.
    """
    content = language.markup_separator.join(
        [
            language.code_block_builder(code="x = []", language="python"),
            language.directive_builder(directive="group", argument="start"),
            language.code_block_builder(code="x = [*x, 1]", language="python"),
            language.directive_builder(directive="skip", argument="start"),
            language.code_block_builder(code="x = [*x, 2]", language="python"),
            language.code_block_builder(code="x = [*x, 3]", language="python"),
            language.directive_builder(directive="skip", argument="end"),
            language.code_block_builder(code="x = [*x, 4]", language="python"),
            language.directive_builder(directive="group", argument="end"),
            language.code_block_builder(code="x = [*x, 5]", language="python"),
        ]
    )
    test_document = tmp_path / "test"
    test_document.write_text(
        data=f"{content}{language.markup_separator}",
        encoding="utf-8",
    )

    evaluator = BlockAccumulatorEvaluator(namespace_key="blocks")
    group_parser = language.group_parser_cls(
        directive="group",
        evaluator=evaluator,
        pad_groups=False,
    )
    code_block_parser = language.code_block_parser_cls(
        language="python",
        evaluator=evaluator,
    )
    skip_parser = language.skip_parser_cls(directive="skip")

    sybil = Sybil(parsers=[code_block_parser, skip_parser, group_parser])
    document = sybil.parse(path=test_document)

    for example in document.examples():
        example.evaluate()

    # Blocks 2 and 3 are skipped by the skip range
    assert document.namespace["blocks"] == [
        "x = []\n",
        "x = [*x, 1]\n\nx = [*x, 4]\n",
        "x = [*x, 5]\n",
    ]


def test_no_argument(language: MarkupLanguage, tmp_path: Path) -> None:
    """
    An error is raised when a group directive has no arguments.
    """
    content = language.markup_separator.join(
        [
            language.directive_builder(directive="group"),
            language.directive_builder(directive="group", argument="end"),
        ]
    )
    test_document = tmp_path / "test"
    test_document.write_text(
        data=f"{content}{language.markup_separator}",
        encoding="utf-8",
    )

    group_parser = language.group_parser_cls(
        directive="group",
        evaluator=NoOpEvaluator(),
        pad_groups=True,
    )

    sybil = Sybil(parsers=[group_parser])
    with pytest.raises(
        expected_exception=ValueError,
        match="missing arguments to group",
    ):
        sybil.parse(path=test_document)


def test_malformed_argument(language: MarkupLanguage, tmp_path: Path) -> None:
    """
    An error is raised when the group directive argument is invalid.
    """
    content = language.markup_separator.join(
        [
            language.directive_builder(
                directive="group",
                argument="not_start_or_end",
            ),
            language.directive_builder(directive="group", argument="end"),
        ]
    )
    test_document = tmp_path / "test"
    test_document.write_text(
        data=f"{content}{language.markup_separator}",
        encoding="utf-8",
    )

    group_parser = language.group_parser_cls(
        directive="group",
        evaluator=NoOpEvaluator(),
        pad_groups=True,
    )

    sybil = Sybil(parsers=[group_parser])
    with pytest.raises(
        expected_exception=ValueError,
        match="malformed arguments to group",
    ):
        sybil.parse(path=test_document)


def test_end_only(language: MarkupLanguage, tmp_path: Path) -> None:
    """
    An error is raised when an end directive has no matching start.
    """
    content = language.directive_builder(directive="group", argument="end")
    test_document = tmp_path / "test"
    test_document.write_text(
        data=f"{content}{language.markup_separator}",
        encoding="utf-8",
    )

    group_parser = language.group_parser_cls(
        directive="group",
        evaluator=NoOpEvaluator(),
        pad_groups=True,
    )

    sybil = Sybil(parsers=[group_parser])
    # Error is raised at parse time since we validate structure upfront
    with pytest.raises(
        expected_exception=ValueError,
        match="'group: end' must follow 'group: start'",
    ):
        sybil.parse(path=test_document)


def test_start_after_start(language: MarkupLanguage, tmp_path: Path) -> None:
    """
    An error is raised when start directives are nested improperly.
    """
    content = language.markup_separator.join(
        [
            language.directive_builder(directive="group", argument="start"),
            language.directive_builder(directive="group", argument="start"),
        ]
    )
    test_document = tmp_path / "test"
    test_document.write_text(
        data=f"{content}{language.markup_separator}",
        encoding="utf-8",
    )

    group_parser = language.group_parser_cls(
        directive="group",
        evaluator=NoOpEvaluator(),
        pad_groups=True,
    )

    sybil = Sybil(parsers=[group_parser])
    with pytest.raises(
        expected_exception=ValueError,
        match="'group: start' was not followed by 'group: end'",
    ):
        sybil.parse(path=test_document)


def test_start_only(language: MarkupLanguage, tmp_path: Path) -> None:
    """
    An error is raised when a group starts but doesn't end.
    """
    content = language.directive_builder(directive="group", argument="start")
    test_document = tmp_path / "test"
    test_document.write_text(
        data=f"{content}{language.markup_separator}",
        encoding="utf-8",
    )

    group_parser = language.group_parser_cls(
        directive="group",
        evaluator=NoOpEvaluator(),
        pad_groups=True,
    )

    sybil = Sybil(parsers=[group_parser])
    with pytest.raises(
        expected_exception=ValueError,
        match="'group: start' was not followed by 'group: end'",
    ):
        sybil.parse(path=test_document)


def test_start_start_end(language: MarkupLanguage, tmp_path: Path) -> None:
    """
    An error is raised when start directives are nested with an end.
    """
    content = language.markup_separator.join(
        [
            language.directive_builder(directive="group", argument="start"),
            language.directive_builder(directive="group", argument="start"),
            language.directive_builder(directive="group", argument="end"),
        ]
    )
    test_document = tmp_path / "test"
    test_document.write_text(
        data=f"{content}{language.markup_separator}",
        encoding="utf-8",
    )

    group_parser = language.group_parser_cls(
        directive="group",
        evaluator=NoOpEvaluator(),
        pad_groups=True,
    )

    sybil = Sybil(parsers=[group_parser])
    # Error is raised at parse time since we validate structure upfront
    with pytest.raises(
        expected_exception=ValueError,
        match="'group: start' was not followed by 'group: end'",
    ):
        sybil.parse(path=test_document)


def test_directive_name_not_regex_escaped(
    language: MarkupLanguage,
    tmp_path: Path,
) -> None:
    """
    Directive names containing regex characters are matched literally.
    """
    directive = "custom-group[has_square_brackets]"
    content = language.markup_separator.join(
        [
            language.code_block_builder(code="x = []", language="python"),
            language.directive_builder(directive=directive, argument="start"),
            language.code_block_builder(code="x = [*x, 1]", language="python"),
            language.code_block_builder(code="x = [*x, 2]", language="python"),
            language.directive_builder(directive=directive, argument="end"),
            language.code_block_builder(code="x = [*x, 3]", language="python"),
            language.directive_builder(directive=directive, argument="start"),
            language.code_block_builder(code="x = [*x, 4]", language="python"),
            language.code_block_builder(code="x = [*x, 5]", language="python"),
            language.directive_builder(directive=directive, argument="end"),
        ]
    )
    test_document = tmp_path / "test"
    test_document.write_text(
        data=f"{content}{language.markup_separator}",
        encoding="utf-8",
    )

    evaluator = BlockAccumulatorEvaluator(namespace_key="blocks")
    group_parser = language.group_parser_cls(
        directive=directive,
        evaluator=evaluator,
        pad_groups=True,
    )
    code_block_parser = language.code_block_parser_cls(
        language="python",
        evaluator=evaluator,
    )

    sybil = Sybil(parsers=[code_block_parser, group_parser])
    document = sybil.parse(path=test_document)

    for example in document.examples():
        example.evaluate()

    separator_newlines = len(language.markup_separator)
    padding_newlines = separator_newlines + 1
    padding = "\n" * padding_newlines

    assert document.namespace["blocks"] == [
        "x = []\n",
        f"x = [*x, 1]\n{padding}x = [*x, 2]\n",
        "x = [*x, 3]\n",
        f"x = [*x, 4]\n{padding}x = [*x, 5]\n",
    ]


def test_with_shell_command_evaluator(
    language: MarkupLanguage,
    tmp_path: Path,
) -> None:
    """
    The group parser cooperates with the shell command evaluator.
    """
    content = language.markup_separator.join(
        [
            language.directive_builder(directive="group", argument="start"),
            language.code_block_builder(code="x = [*x, 1]", language="python"),
            language.code_block_builder(code="x = [*x, 2]", language="python"),
            language.directive_builder(directive="group", argument="end"),
        ]
    )
    test_document = tmp_path / "test"
    test_document.write_text(
        data=f"{content}{language.markup_separator}",
        encoding="utf-8",
    )

    output_document = tmp_path / "output.txt"
    shell_evaluator = ShellCommandEvaluator(
        args=["sh", "-c", f"cat $0 > {output_document.as_posix()}"],
        pad_file=True,
        write_to_file=False,
        use_pty=False,
    )
    group_parser = language.group_parser_cls(
        directive="group",
        evaluator=shell_evaluator,
        pad_groups=True,
    )
    code_block_parser = language.code_block_parser_cls(language="python")

    sybil = Sybil(parsers=[code_block_parser, group_parser])
    document = sybil.parse(path=test_document)

    for example in document.examples():
        example.evaluate()

    output_document_content = output_document.read_text(encoding="utf-8")

    separator_newlines = len(language.markup_separator)
    padding_newlines = separator_newlines + 1

    leading_padding = "\n" * (separator_newlines * 2)
    block_padding = "\n" * padding_newlines

    expected_output_document_content = (
        f"{leading_padding}x = [*x, 1]\n{block_padding}x = [*x, 2]\n"
    )
    assert output_document_content == expected_output_document_content


def test_state_cleanup_on_evaluator_failure(
    language: MarkupLanguage,
    tmp_path: Path,
) -> None:
    """When an evaluator raises an exception, the grouper state is cleaned up.

    This ensures that subsequent groups in the same document can be
    evaluated without getting misleading errors about mismatched
    start/end directives.
    """
    content = language.markup_separator.join(
        [
            language.directive_builder(directive="group", argument="start"),
            language.code_block_builder(code="exit 1", language="bash"),
            language.directive_builder(directive="group", argument="end"),
            language.directive_builder(directive="group", argument="start"),
            language.code_block_builder(code="exit 0", language="bash"),
            language.directive_builder(directive="group", argument="end"),
        ]
    )
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
    group_parser = language.group_parser_cls(
        directive="group",
        evaluator=shell_evaluator,
        pad_groups=False,
    )
    code_block_parser = language.code_block_parser_cls(language="bash")

    sybil = Sybil(parsers=[code_block_parser, group_parser])
    document = sybil.parse(path=test_document)

    (
        first_group_start,
        first_code_block,
        first_group_end,
        second_group_start,
        second_code_block,
        second_group_end,
    ) = document.examples()

    first_group_start.evaluate()
    first_code_block.evaluate()

    with pytest.raises(expected_exception=subprocess.CalledProcessError):
        first_group_end.evaluate()

    second_group_start.evaluate()
    second_code_block.evaluate()
    second_group_end.evaluate()


def test_thread_safety(language: MarkupLanguage, tmp_path: Path) -> None:
    """
    The group parser is thread-safe when examples are evaluated concurrently.
    """
    content = language.markup_separator.join(
        [
            language.directive_builder(directive="group", argument="start"),
            language.code_block_builder(code="x = [*x, 1]", language="python"),
            language.code_block_builder(code="x = [*x, 2]", language="python"),
            language.directive_builder(directive="group", argument="end"),
        ]
    )
    test_document = tmp_path / "test"
    test_document.write_text(
        data=f"{content}{language.markup_separator}",
        encoding="utf-8",
    )

    evaluator = BlockAccumulatorEvaluator(namespace_key="blocks")
    group_parser = language.group_parser_cls(
        directive="group",
        evaluator=evaluator,
        pad_groups=True,
    )
    code_block_parser = language.code_block_parser_cls(
        language="python",
        evaluator=evaluator,
    )

    sybil = Sybil(parsers=[code_block_parser, group_parser])
    document = sybil.parse(path=test_document)

    examples: list[Example] = list(document.examples())

    def evaluate(ex: Example) -> None:
        """
        Evaluate the example.
        """
        ex.evaluate()

    with ThreadPoolExecutor(max_workers=4) as executor:
        list(executor.map(evaluate, examples))

    separator_newlines = len(language.markup_separator)
    padding_newlines = separator_newlines + 1
    padding = "\n" * padding_newlines

    assert document.namespace["blocks"] == [
        f"x = [*x, 1]\n{padding}x = [*x, 2]\n",
    ]


def test_multiple_groups_concurrent_evaluation(
    language: MarkupLanguage,
    tmp_path: Path,
) -> None:
    """Multiple groups in the same document can be evaluated concurrently.

    This tests the core race condition fix where multiple groups in the
    same document are processed in parallel without interfering with
    each other. The code blocks within groups can be evaluated
    concurrently, but start/end markers must be evaluated in order
    (start before end).
    """
    content = language.markup_separator.join(
        [
            language.directive_builder(directive="group", argument="start"),
            language.code_block_builder(code="x = [1]", language="python"),
            language.code_block_builder(code="x = [*x, 2]", language="python"),
            language.directive_builder(directive="group", argument="end"),
            language.directive_builder(directive="group", argument="start"),
            language.code_block_builder(code="y = [3]", language="python"),
            language.code_block_builder(code="y = [*y, 4]", language="python"),
            language.directive_builder(directive="group", argument="end"),
        ]
    )
    test_document = tmp_path / "test"
    test_document.write_text(
        data=f"{content}{language.markup_separator}",
        encoding="utf-8",
    )

    evaluator = BlockAccumulatorEvaluator(namespace_key="blocks")
    group_parser = language.group_parser_cls(
        directive="group",
        evaluator=evaluator,
        pad_groups=True,
    )
    code_block_parser = language.code_block_parser_cls(
        language="python",
        evaluator=evaluator,
    )

    sybil = Sybil(parsers=[code_block_parser, group_parser])
    document = sybil.parse(path=test_document)

    examples: list[Example] = list(document.examples())
    start1, code1a, code1b, end1, start2, code2a, code2b, end2 = examples

    # Evaluate start markers first (required ordering)
    start1.evaluate()
    start2.evaluate()

    def evaluate(ex: Example) -> None:
        """
        Evaluate an example.
        """
        ex.evaluate()

    code_blocks = [code1a, code1b, code2a, code2b]
    with ThreadPoolExecutor(max_workers=4) as executor:
        list(executor.map(evaluate, code_blocks))

    # Evaluate end markers (required ordering after start)
    end1.evaluate()
    end2.evaluate()

    separator_newlines = len(language.markup_separator)
    padding_newlines = separator_newlines + 1
    padding = "\n" * padding_newlines

    # Both groups should have been evaluated correctly
    assert document.namespace["blocks"] == [
        f"x = [1]\n{padding}x = [*x, 2]\n",
        f"y = [3]\n{padding}y = [*y, 4]\n",
    ]


def test_evaluation_order_independence(
    language: MarkupLanguage,
    tmp_path: Path,
) -> None:
    """
    Examples can be evaluated out of order and still produce correct results.
    """
    content = language.markup_separator.join(
        [
            language.directive_builder(directive="group", argument="start"),
            language.code_block_builder(code="x = [1]", language="python"),
            language.code_block_builder(code="x = [*x, 2]", language="python"),
            language.directive_builder(directive="group", argument="end"),
        ]
    )
    test_document = tmp_path / "test"
    test_document.write_text(
        data=f"{content}{language.markup_separator}",
        encoding="utf-8",
    )

    evaluator = BlockAccumulatorEvaluator(namespace_key="blocks")
    group_parser = language.group_parser_cls(
        directive="group",
        evaluator=evaluator,
        pad_groups=True,
    )
    code_block_parser = language.code_block_parser_cls(
        language="python",
        evaluator=evaluator,
    )

    sybil = Sybil(parsers=[code_block_parser, group_parser])
    document = sybil.parse(path=test_document)

    examples: list[Example] = list(document.examples())
    # Order: start, code1, code2, end
    start, code1, code2, end = examples

    # Evaluate in a different order: code2, start, code1, end
    code2.evaluate()
    start.evaluate()
    code1.evaluate()
    end.evaluate()

    separator_newlines = len(language.markup_separator)
    padding_newlines = separator_newlines + 1
    padding = "\n" * padding_newlines

    # Despite out-of-order evaluation, the result should be sorted by position
    assert document.namespace["blocks"] == [
        f"x = [1]\n{padding}x = [*x, 2]\n",
    ]


def test_no_group_directives(language: MarkupLanguage, tmp_path: Path) -> None:
    """The group parser handles documents with no group directives.

    When a document has code blocks but no group directives, the group
    parser should not affect the document.
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
    group_parser = language.group_parser_cls(
        directive="group",
        evaluator=evaluator,
        pad_groups=True,
    )
    code_block_parser = language.code_block_parser_cls(
        language="python",
        evaluator=evaluator,
    )

    sybil = Sybil(parsers=[code_block_parser, group_parser])
    document = sybil.parse(path=test_document)

    for example in document.examples():
        example.evaluate()

    # Code blocks are evaluated individually, not grouped
    assert document.namespace["blocks"] == [
        "x = [1]\n",
        "x = [*x, 2]\n",
    ]


def test_no_pad_groups(language: MarkupLanguage, tmp_path: Path) -> None:
    """
    It is possible to avoid padding grouped code blocks.
    """
    content = language.markup_separator.join(
        [
            language.directive_builder(directive="group", argument="start"),
            language.code_block_builder(code="x = [*x, 1]", language="python"),
            language.code_block_builder(code="x = [*x, 2]", language="python"),
            language.directive_builder(directive="group", argument="end"),
        ]
    )
    test_document = tmp_path / "test"
    test_document.write_text(
        data=f"{content}{language.markup_separator}",
        encoding="utf-8",
    )

    output_document = tmp_path / "output.txt"
    shell_evaluator = ShellCommandEvaluator(
        args=["sh", "-c", f"cat $0 > {output_document.as_posix()}"],
        pad_file=True,
        write_to_file=False,
        use_pty=False,
    )
    group_parser = language.group_parser_cls(
        directive="group",
        evaluator=shell_evaluator,
        pad_groups=False,
    )
    code_block_parser = language.code_block_parser_cls(language="python")

    sybil = Sybil(parsers=[code_block_parser, group_parser])
    document = sybil.parse(path=test_document)

    for example in document.examples():
        example.evaluate()

    output_document_content = output_document.read_text(encoding="utf-8")

    separator_newlines = len(language.markup_separator)
    leading_padding = "\n" * (separator_newlines * 2)

    expected_output_document_content = (
        f"{leading_padding}x = [*x, 1]\n\nx = [*x, 2]\n"
    )
    assert output_document_content == expected_output_document_content


def test_end_marker_waits_for_code_blocks(
    language: MarkupLanguage,
    tmp_path: Path,
) -> None:
    """The end marker waits for all code blocks to be collected.

    This tests the fix for a race condition where the end marker could
    be evaluated before all code blocks were collected, resulting in
    incomplete groups. The end marker now waits until all expected code
    blocks have been collected before processing the group.
    """
    content = language.markup_separator.join(
        [
            language.directive_builder(directive="group", argument="start"),
            language.code_block_builder(code="x = [1]", language="python"),
            language.code_block_builder(code="x = [*x, 2]", language="python"),
            language.directive_builder(directive="group", argument="end"),
        ]
    )
    test_document = tmp_path / "test"
    test_document.write_text(
        data=f"{content}{language.markup_separator}",
        encoding="utf-8",
    )

    evaluator = BlockAccumulatorEvaluator(namespace_key="blocks")
    group_parser = language.group_parser_cls(
        directive="group",
        evaluator=evaluator,
        pad_groups=True,
    )
    code_block_parser = language.code_block_parser_cls(
        language="python",
        evaluator=evaluator,
    )

    sybil = Sybil(parsers=[code_block_parser, group_parser])
    document = sybil.parse(path=test_document)

    examples: list[Example] = list(document.examples())
    start, code1, code2, end = examples

    # Evaluate start marker first
    start.evaluate()

    # Evaluate end marker AND code blocks concurrently.
    # Without the fix, the end marker could complete before code blocks
    # are collected, resulting in an empty or partial group.
    # With the fix, the end marker waits for all code blocks.
    def evaluate(ex: Example) -> None:
        """
        Evaluate the example.
        """
        ex.evaluate()

    # Run all three concurrently - end marker should wait for code blocks
    with ThreadPoolExecutor(max_workers=3) as executor:
        list(executor.map(evaluate, [end, code1, code2]))

    separator_newlines = len(language.markup_separator)
    padding_newlines = separator_newlines + 1
    padding = "\n" * padding_newlines

    # Both code blocks should be in the group, properly combined
    assert document.namespace["blocks"] == [
        f"x = [1]\n{padding}x = [*x, 2]\n",
    ]
