"""
Unified tests for the GroupedSourceParser across markup languages.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from sybil_extras.evaluators.block_accumulator import BlockAccumulatorEvaluator
from sybil_extras.evaluators.no_op import NoOpEvaluator
from sybil_extras.evaluators.shell_evaluator import ShellCommandEvaluator

from ._markups import (
    MARKUP_LANGUAGES,
    MarkupLanguage,
    evaluate_document,
    parse_document,
)


@pytest.fixture(params=MARKUP_LANGUAGES, ids=lambda markup: markup.name)
def markup_language(request: pytest.FixtureRequest) -> MarkupLanguage:
    """
    Parameterize grouped source parser tests.
    """
    assert isinstance(request.param, MarkupLanguage)
    return request.param


def _make_group_parser(
    markup_language: MarkupLanguage,
    *,
    evaluator: Evaluator,
    pad_groups: bool,
    directive: str = "group",
) -> Parser:
    """
    Build a grouped source parser for the provided directive.
    """
    return markup_language.grouped_source_parser_cls(
        directive=directive,
        evaluator=evaluator,
        pad_groups=pad_groups,
    )


def test_group(markup_language: MarkupLanguage, tmp_path: Path) -> None:
    """
    The group parser groups examples.
    """
    evaluator = BlockAccumulatorEvaluator(namespace_key="blocks")
    group_parser = _make_group_parser(
        markup_language=markup_language,
        evaluator=evaluator,
        pad_groups=True,
    )
    code_block_parser = markup_language.code_block_parser_cls(
        language="python",
        evaluator=evaluator,
    )

    document = evaluate_document(
        tmp_path=tmp_path,
        markup=markup_language,
        parts=[
            markup_language.code_block("x = []"),
            markup_language.directive("group: start"),
            markup_language.code_block("x = [*x, 1]"),
            markup_language.code_block("x = [*x, 2]"),
            markup_language.directive("group: end"),
            markup_language.code_block("x = [*x, 3]"),
            markup_language.directive("group: start"),
            markup_language.code_block("x = [*x, 4]"),
            markup_language.code_block("x = [*x, 5]"),
            markup_language.directive("group: end"),
        ],
        parsers=[code_block_parser, group_parser],
    )

    assert document.namespace["blocks"] == [
        "x = []\n",
        "x = [*x, 1]\n\n\n\nx = [*x, 2]\n",
        "x = [*x, 3]\n",
        "x = [*x, 4]\n\n\n\nx = [*x, 5]\n",
    ]


def test_nothing_after_group(
    markup_language: MarkupLanguage, tmp_path: Path
) -> None:
    """
    The group parser groups examples even at the end of a document.
    """
    evaluator = BlockAccumulatorEvaluator(namespace_key="blocks")
    group_parser = _make_group_parser(
        markup_language=markup_language,
        evaluator=evaluator,
        pad_groups=True,
    )
    code_block_parser = markup_language.code_block_parser_cls(
        language="python",
        evaluator=evaluator,
    )

    document = evaluate_document(
        tmp_path=tmp_path,
        markup=markup_language,
        parts=[
            markup_language.code_block("x = []"),
            markup_language.directive("group: start"),
            markup_language.code_block("x = [*x, 1]"),
            markup_language.code_block("x = [*x, 2]"),
            markup_language.directive("group: end"),
        ],
        parsers=[code_block_parser, group_parser],
    )

    assert document.namespace["blocks"] == [
        "x = []\n",
        "x = [*x, 1]\n\n\n\nx = [*x, 2]\n",
    ]


def test_empty_group(markup_language: MarkupLanguage, tmp_path: Path) -> None:
    """
    The group parser groups examples even when the group is empty.
    """
    evaluator = BlockAccumulatorEvaluator(namespace_key="blocks")
    group_parser = _make_group_parser(
        markup_language=markup_language,
        evaluator=evaluator,
        pad_groups=True,
    )
    code_block_parser = markup_language.code_block_parser_cls(
        language="python",
        evaluator=evaluator,
    )

    document = evaluate_document(
        tmp_path=tmp_path,
        markup=markup_language,
        parts=[
            markup_language.code_block("x = []"),
            markup_language.directive("group: start"),
            markup_language.directive("group: end"),
            markup_language.code_block("x = [*x, 3]"),
        ],
        parsers=[code_block_parser, group_parser],
    )

    assert document.namespace["blocks"] == [
        "x = []\n",
        markup_language.expected_text("x = [*x, 3]"),
    ]


def test_group_with_skip(
    markup_language: MarkupLanguage, tmp_path: Path
) -> None:
    """
    Skip directives are respected within a group.
    """
    evaluator = BlockAccumulatorEvaluator(namespace_key="blocks")
    group_parser = _make_group_parser(
        markup_language=markup_language,
        evaluator=evaluator,
        pad_groups=True,
    )
    code_block_parser = markup_language.code_block_parser_cls(
        language="python",
        evaluator=evaluator,
    )
    skip_parser = (
        markup_language.skip_parser_cls()
        if markup_language.skip_parser_cls
        else None
    )

    parsers = [code_block_parser, group_parser]
    if skip_parser is not None:
        parsers.insert(1, skip_parser)

    document = evaluate_document(
        tmp_path=tmp_path,
        markup=markup_language,
        parts=[
            markup_language.code_block("x = []"),
            markup_language.directive("group: start"),
            markup_language.code_block("x = [*x, 1]"),
            markup_language.directive("skip: next"),
            markup_language.code_block("x = [*x, 2]"),
            markup_language.directive("group: end"),
            markup_language.code_block("x = [*x, 3]"),
        ],
        parsers=parsers,
    )

    assert document.namespace["blocks"] == [
        "x = []\n",
        "x = [*x, 1]\n",
        markup_language.expected_text("x = [*x, 3]"),
    ]


def test_no_argument(markup_language: MarkupLanguage, tmp_path: Path) -> None:
    """
    An error is raised when a group directive has no arguments.
    """
    missing_arg = "group:" if markup_language.extension == "rst" else "group"
    group_parser = _make_group_parser(
        markup_language=markup_language,
        evaluator=NoOpEvaluator(),
        pad_groups=True,
    )

    with pytest.raises(ValueError, match=r"missing arguments to group"):
        parse_document(
            tmp_path=tmp_path,
            markup=markup_language,
            parts=[
                markup_language.directive(missing_arg),
                markup_language.directive("group: end"),
            ],
            parsers=[group_parser],
        )


def test_malformed_argument(
    markup_language: MarkupLanguage, tmp_path: Path
) -> None:
    """
    An error is raised when a group directive has malformed arguments.
    """
    group_parser = _make_group_parser(
        markup_language=markup_language,
        evaluator=NoOpEvaluator(),
        pad_groups=True,
    )

    with pytest.raises(
        ValueError,
        match=r"malformed arguments to group: 'not_start_or_end'",
    ):
        parse_document(
            tmp_path=tmp_path,
            markup=markup_language,
            parts=[
                markup_language.directive("group: not_start_or_end"),
                markup_language.directive("group: end"),
            ],
            parsers=[group_parser],
        )


def test_end_only(markup_language: MarkupLanguage, tmp_path: Path) -> None:
    """
    An error is raised when a group end directive is given with no start.
    """
    group_parser = _make_group_parser(
        markup_language=markup_language,
        evaluator=NoOpEvaluator(),
        pad_groups=True,
    )

    document = parse_document(
        tmp_path=tmp_path,
        markup=markup_language,
        parts=[markup_language.directive("group: end")],
        parsers=[group_parser],
    )
    (example,) = document.examples()
    with pytest.raises(
        ValueError,
        match=r"'group: end' must follow 'group: start'",
    ):
        example.evaluate()


def test_start_after_start(
    markup_language: MarkupLanguage, tmp_path: Path
) -> None:
    """
    An error is raised when a group start directive is given after another
    start.
    """
    group_parser = _make_group_parser(
        markup_language=markup_language,
        evaluator=NoOpEvaluator(),
        pad_groups=True,
    )

    document = parse_document(
        tmp_path=tmp_path,
        markup=markup_language,
        parts=[
            markup_language.directive("group: start"),
            markup_language.directive("group: start"),
        ],
        parsers=[group_parser],
    )

    first_start_example, second_start_example = document.examples()
    first_start_example.evaluate()

    with pytest.raises(
        ValueError,
        match=r"'group: start' must be followed by 'group: end'",
    ):
        second_start_example.evaluate()


def test_directive_name_not_regex_escaped(
    markup_language: MarkupLanguage,
    tmp_path: Path,
) -> None:
    """
    If the directive name is not regex-escaped, it is still matched.
    """
    evaluator = BlockAccumulatorEvaluator(namespace_key="blocks")
    directive_name = "custom-group[has_square_brackets]"
    group_parser = _make_group_parser(
        markup_language=markup_language,
        evaluator=evaluator,
        pad_groups=True,
        directive=directive_name,
    )
    code_block_parser = markup_language.code_block_parser_cls(
        language="python",
        evaluator=evaluator,
    )

    document = evaluate_document(
        tmp_path=tmp_path,
        markup=markup_language,
        parts=[
            markup_language.code_block("x = []"),
            markup_language.directive(f"{directive_name}: start"),
            markup_language.code_block("x = [*x, 1]"),
            markup_language.code_block("x = [*x, 2]"),
            markup_language.directive(f"{directive_name}: end"),
            markup_language.code_block("x = [*x, 3]"),
            markup_language.directive(f"{directive_name}: start"),
            markup_language.code_block("x = [*x, 4]"),
            markup_language.code_block("x = [*x, 5]"),
            markup_language.directive(f"{directive_name}: end"),
        ],
        parsers=[code_block_parser, group_parser],
    )

    assert document.namespace["blocks"] == [
        "x = []\n",
        "x = [*x, 1]\n\n\n\nx = [*x, 2]\n",
        "x = [*x, 3]\n",
        "x = [*x, 4]\n\n\n\nx = [*x, 5]\n",
    ]


def _expected_shell_output(
    markup_language: MarkupLanguage,
    *,
    pad_groups: bool,
) -> str:
    """
    Compute the expected shell output for the grouped blocks.
    """
    start_newlines = 4 if markup_language.extension == "rst" else 3
    between_newlines = 4 if pad_groups else 2
    return (
        ("\n" * start_newlines)
        + "x = [*x, 1]\n"
        + ("\n" * (between_newlines - 1))
        + "x = [*x, 2]\n"
    )


def test_with_shell_command_evaluator(
    markup_language: MarkupLanguage,
    tmp_path: Path,
) -> None:
    """
    The group parser feeds combined blocks to the shell evaluator.
    """
    output_document = tmp_path / "output.txt"
    shell_evaluator = ShellCommandEvaluator(
        args=["sh", "-c", f"cat $0 > {output_document.as_posix()}"],
        pad_file=True,
        write_to_file=False,
        use_pty=False,
    )
    group_parser = _make_group_parser(
        markup_language=markup_language,
        evaluator=shell_evaluator,
        pad_groups=True,
    )
    code_block_parser = markup_language.code_block_parser_cls(
        language="python"
    )

    document = evaluate_document(
        tmp_path=tmp_path,
        markup=markup_language,
        parts=[
            markup_language.directive("group: start"),
            markup_language.code_block("x = [*x, 1]"),
            markup_language.code_block("x = [*x, 2]"),
            markup_language.directive("group: end"),
        ],
        parsers=[code_block_parser, group_parser],
    )
    assert not document.namespace

    output_document_content = output_document.read_text(encoding="utf-8")
    assert output_document_content == _expected_shell_output(
        markup_language=markup_language,
        pad_groups=True,
    )


def test_no_pad_groups(
    markup_language: MarkupLanguage, tmp_path: Path
) -> None:
    """
    It is possible to avoid padding the groups.
    """
    output_document = tmp_path / "output.txt"
    shell_evaluator = ShellCommandEvaluator(
        args=["sh", "-c", f"cat $0 > {output_document.as_posix()}"],
        pad_file=True,
        write_to_file=False,
        use_pty=False,
    )
    group_parser = _make_group_parser(
        markup_language=markup_language,
        evaluator=shell_evaluator,
        pad_groups=False,
    )
    code_block_parser = markup_language.code_block_parser_cls(
        language="python"
    )

    evaluate_document(
        tmp_path=tmp_path,
        markup=markup_language,
        parts=[
            markup_language.directive("group: start"),
            markup_language.code_block("x = [*x, 1]"),
            markup_language.code_block("x = [*x, 2]"),
            markup_language.directive("group: end"),
        ],
        parsers=[code_block_parser, group_parser],
    )

    output_document_content = output_document.read_text(encoding="utf-8")
    assert output_document_content == _expected_shell_output(
        markup_language=markup_language,
        pad_groups=False,
    )
