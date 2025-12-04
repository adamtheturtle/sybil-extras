"""
Grouped source parser tests shared across markup languages.
"""

import textwrap
from pathlib import Path

import pytest
from sybil import Sybil

from sybil_extras.evaluators.block_accumulator import BlockAccumulatorEvaluator
from sybil_extras.evaluators.no_op import NoOpEvaluator
from sybil_extras.evaluators.shell_evaluator import ShellCommandEvaluator
from sybil_extras.languages import RESTRUCTUREDTEXT, MarkupLanguage
from tests.helpers import join_markup


def test_group(language: MarkupLanguage, tmp_path: Path) -> None:
    """
    The group parser groups examples.
    """
    content = join_markup(
        language,
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
    )
    test_document = tmp_path / f"test{language.file_extension}"
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
        "x = [*x, 1]\n\n\n\nx = [*x, 2]\n",
        "x = [*x, 3]\n",
        "x = [*x, 4]\n\n\n\nx = [*x, 5]\n",
    ]


def test_nothing_after_group(language: MarkupLanguage, tmp_path: Path) -> None:
    """
    Groups are handled even at the end of a document.
    """
    content = join_markup(
        language,
        language.code_block_builder(code="x = []", language="python"),
        language.directive_builder(directive="group", argument="start"),
        language.code_block_builder(code="x = [*x, 1]", language="python"),
        language.code_block_builder(code="x = [*x, 2]", language="python"),
        language.directive_builder(directive="group", argument="end"),
    )
    test_document = tmp_path / f"test{language.file_extension}"
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
        "x = [*x, 1]\n\n\n\nx = [*x, 2]\n",
    ]


def test_empty_group(language: MarkupLanguage, tmp_path: Path) -> None:
    """
    Empty groups are handled gracefully.
    """
    content = join_markup(
        language,
        language.code_block_builder(code="x = []", language="python"),
        language.directive_builder(directive="group", argument="start"),
        language.directive_builder(directive="group", argument="end"),
        language.code_block_builder(code="x = [*x, 3]", language="python"),
    )
    test_document = tmp_path / f"test{language.file_extension}"
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
    content = join_markup(
        language,
        language.code_block_builder(code="x = []", language="python"),
        language.directive_builder(directive="group", argument="start"),
        language.code_block_builder(code="x = [*x, 1]", language="python"),
        language.directive_builder(directive="skip", argument="next"),
        language.code_block_builder(code="x = [*x, 2]", language="python"),
        language.directive_builder(directive="group", argument="end"),
        language.code_block_builder(code="x = [*x, 3]", language="python"),
    )
    test_document = tmp_path / f"test{language.file_extension}"
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


def test_no_argument(language: MarkupLanguage, tmp_path: Path) -> None:
    """
    An error is raised when a group directive has no arguments.
    """
    content = join_markup(
        language,
        language.directive_builder(directive="group"),
        language.directive_builder(directive="group", argument="end"),
    )
    test_document = tmp_path / f"test{language.file_extension}"
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
    content = join_markup(
        language,
        language.directive_builder(
            directive="group",
            argument="not_start_or_end",
        ),
        language.directive_builder(directive="group", argument="end"),
    )
    test_document = tmp_path / f"test{language.file_extension}"
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
    test_document = tmp_path / f"test{language.file_extension}"
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
    document = sybil.parse(path=test_document)

    (example,) = document.examples()
    with pytest.raises(
        expected_exception=ValueError,
        match="'group: end' must follow 'group: start'",
    ):
        example.evaluate()


def test_start_after_start(language: MarkupLanguage, tmp_path: Path) -> None:
    """
    An error is raised when start directives are nested improperly.
    """
    content = join_markup(
        language,
        language.directive_builder(directive="group", argument="start"),
        language.directive_builder(directive="group", argument="start"),
    )
    test_document = tmp_path / f"test{language.file_extension}"
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
    document = sybil.parse(path=test_document)

    first_start_example, second_start_example = document.examples()
    first_start_example.evaluate()
    with pytest.raises(
        expected_exception=ValueError,
        match="'group: start' must be followed by 'group: end'",
    ):
        second_start_example.evaluate()


def test_directive_name_not_regex_escaped(
    language: MarkupLanguage,
    tmp_path: Path,
) -> None:
    """
    Directive names containing regex characters are matched literally.
    """
    directive = "custom-group[has_square_brackets]"
    content = join_markup(
        language,
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
    )
    test_document = tmp_path / f"test{language.file_extension}"
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

    assert document.namespace["blocks"] == [
        "x = []\n",
        "x = [*x, 1]\n\n\n\nx = [*x, 2]\n",
        "x = [*x, 3]\n",
        "x = [*x, 4]\n\n\n\nx = [*x, 5]\n",
    ]


def test_with_shell_command_evaluator(
    language: MarkupLanguage,
    tmp_path: Path,
) -> None:
    """
    The group parser cooperates with the shell command evaluator.
    """
    content = join_markup(
        language,
        language.directive_builder(directive="group", argument="start"),
        language.code_block_builder(code="x = [*x, 1]", language="python"),
        language.code_block_builder(code="x = [*x, 2]", language="python"),
        language.directive_builder(directive="group", argument="end"),
    )
    test_document = tmp_path / f"test{language.file_extension}"
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
    expected_output_document_content = textwrap.dedent(
        text="""\



        x = [*x, 1]



        x = [*x, 2]
            """,
    )
    if language is RESTRUCTUREDTEXT:
        expected_output_document_content = (
            f"\n{expected_output_document_content}"
        )
    assert output_document_content == expected_output_document_content


def test_no_pad_groups(language: MarkupLanguage, tmp_path: Path) -> None:
    """
    It is possible to avoid padding grouped code blocks.
    """
    content = join_markup(
        language,
        language.directive_builder(directive="group", argument="start"),
        language.code_block_builder(code="x = [*x, 1]", language="python"),
        language.code_block_builder(code="x = [*x, 2]", language="python"),
        language.directive_builder(directive="group", argument="end"),
    )
    test_document = tmp_path / f"test{language.file_extension}"
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
    expected_output_document_content = textwrap.dedent(
        text="""\



        x = [*x, 1]

        x = [*x, 2]
            """,
    )
    if language is RESTRUCTUREDTEXT:
        expected_output_document_content = (
            f"\n{expected_output_document_content}"
        )
    assert output_document_content == expected_output_document_content
