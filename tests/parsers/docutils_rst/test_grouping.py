"""Tests for DOCUTILS_RST no_pad_separator_lines=2 behavior."""

import uuid
from pathlib import Path

from beartype import beartype
from sybil import Example, Sybil

from sybil_extras.evaluators.block_accumulator import BlockAccumulatorEvaluator
from sybil_extras.evaluators.shell_evaluator import ShellCommandEvaluator
from sybil_extras.languages import DOCUTILS_RST
from sybil_extras.parsers.docutils_rst.codeblock import CodeBlockParser
from sybil_extras.parsers.docutils_rst.custom_directive_skip import (
    CustomDirectiveSkipParser,
)
from sybil_extras.parsers.docutils_rst.group_all import (
    GroupAllParser,
)
from sybil_extras.parsers.docutils_rst.grouped_source import (
    GroupedSourceParser,
)


@beartype
def make_temp_file_path(*, example: Example) -> Path:
    """Create a temporary file path for an example code block."""
    return Path(example.path).parent / f"temp_{uuid.uuid4().hex[:8]}.py"


def test_group_all_no_pad(tmp_path: Path) -> None:
    """DOCUTILS_RST group-all uses 2 separator lines when pad_groups=False."""
    content = DOCUTILS_RST.markup_separator.join(
        [
            DOCUTILS_RST.code_block_builder(code="x = []", language="python"),
            DOCUTILS_RST.code_block_builder(
                code="x = [*x, 1]", language="python"
            ),
            DOCUTILS_RST.code_block_builder(
                code="x = [*x, 2]", language="python"
            ),
        ]
    )
    test_document = tmp_path / "test"
    test_document.write_text(
        data=f"{content}{DOCUTILS_RST.markup_separator}",
        encoding="utf-8",
    )

    evaluator = BlockAccumulatorEvaluator(namespace_key="blocks")
    group_all_parser = GroupAllParser(
        evaluator=evaluator,
        pad_groups=False,
        no_pad_separator_lines=2,
    )
    code_block_parser = CodeBlockParser(
        language="python",
        evaluator=evaluator,
    )

    sybil = Sybil(parsers=[code_block_parser, group_all_parser])
    document = sybil.parse(path=test_document)

    for example in document.examples():
        example.evaluate()

    blocks = ["x = []", "x = [*x, 1]", "x = [*x, 2]"]
    padding = "\n\n\n"
    expected = padding.join(blocks) + "\n"
    assert document.namespace["blocks"] == [expected]


def test_group_with_skip_range(tmp_path: Path) -> None:
    """DOCUTILS_RST grouped source uses 2 separator lines with skip ranges."""
    directive_builder = DOCUTILS_RST.directive_builders[0]
    content = DOCUTILS_RST.markup_separator.join(
        [
            DOCUTILS_RST.code_block_builder(code="x = []", language="python"),
            directive_builder(directive="group", argument="start"),
            DOCUTILS_RST.code_block_builder(
                code="x = [*x, 1]", language="python"
            ),
            directive_builder(directive="skip", argument="start"),
            DOCUTILS_RST.code_block_builder(
                code="x = [*x, 2]", language="python"
            ),
            DOCUTILS_RST.code_block_builder(
                code="x = [*x, 3]", language="python"
            ),
            directive_builder(directive="skip", argument="end"),
            DOCUTILS_RST.code_block_builder(
                code="x = [*x, 4]", language="python"
            ),
            directive_builder(directive="group", argument="end"),
            DOCUTILS_RST.code_block_builder(
                code="x = [*x, 5]", language="python"
            ),
        ]
    )
    test_document = tmp_path / "test"
    test_document.write_text(
        data=f"{content}{DOCUTILS_RST.markup_separator}",
        encoding="utf-8",
    )

    evaluator = BlockAccumulatorEvaluator(namespace_key="blocks")
    group_parser = GroupedSourceParser(
        directive="group",
        evaluator=evaluator,
        pad_groups=False,
        no_pad_separator_lines=2,
    )
    code_block_parser = CodeBlockParser(
        language="python",
        evaluator=evaluator,
    )
    skip_parser = CustomDirectiveSkipParser(directive="skip")

    sybil = Sybil(parsers=[code_block_parser, skip_parser, group_parser])
    document = sybil.parse(path=test_document)

    for example in document.examples():
        example.evaluate()

    # Blocks 2 and 3 are skipped by the skip range.
    # DOCUTILS_RST uses no_pad_separator_lines=2.
    assert document.namespace["blocks"] == [
        "x = []\n",
        "x = [*x, 1]\n\n\nx = [*x, 4]\n",
        "x = [*x, 5]\n",
    ]


def test_no_pad_groups(tmp_path: Path) -> None:
    """DOCUTILS_RST grouped source uses 2 separator lines with
    pad_groups=False.
    """
    directive_builder = DOCUTILS_RST.directive_builders[0]
    content = DOCUTILS_RST.markup_separator.join(
        [
            directive_builder(directive="group", argument="start"),
            DOCUTILS_RST.code_block_builder(
                code="x = [*x, 1]", language="python"
            ),
            DOCUTILS_RST.code_block_builder(
                code="x = [*x, 2]", language="python"
            ),
            directive_builder(directive="group", argument="end"),
        ]
    )
    test_document = tmp_path / "test"
    test_document.write_text(
        data=f"{content}{DOCUTILS_RST.markup_separator}",
        encoding="utf-8",
    )

    output_document = tmp_path / "output.txt"
    shell_evaluator = ShellCommandEvaluator(
        args=["sh", "-c", f"cat $0 > {output_document.as_posix()}"],
        temp_file_path_maker=make_temp_file_path,
        pad_file=True,
        write_to_file=False,
        use_pty=False,
    )
    group_parser = GroupedSourceParser(
        directive="group",
        evaluator=shell_evaluator,
        pad_groups=False,
        no_pad_separator_lines=2,
    )
    code_block_parser = CodeBlockParser(language="python")

    sybil = Sybil(parsers=[code_block_parser, group_parser])
    document = sybil.parse(path=test_document)

    # Get line number from the first code block to compute expected padding.
    examples = list(document.examples())
    first_code_block = examples[1]
    first_line = first_code_block.line + first_code_block.parsed.line_offset

    for example in examples:
        example.evaluate()

    output_document_content = output_document.read_text(encoding="utf-8")

    # no_pad_separator_lines=2: 2 blank lines between blocks.
    leading_padding = "\n" * first_line
    expected_output_document_content = (
        f"{leading_padding}x = [*x, 1]\n\n\nx = [*x, 2]\n"
    )
    assert output_document_content == expected_output_document_content
