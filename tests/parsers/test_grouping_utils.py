"""Public-interface tests for conditional skip counting in grouping."""

# pylint: disable=wrong-spelling-in-comment

from collections.abc import Iterable
from contextlib import suppress
from pathlib import Path
from unittest import SkipTest

import pytest
from sybil import Document, Region, Sybil
from sybil.parsers.rest import (
    CodeBlockParser as RestCodeBlockParser,
)

from sybil_extras.evaluators.block_accumulator import BlockAccumulatorEvaluator
from sybil_extras.evaluators.no_op import NoOpEvaluator
from sybil_extras.languages import DirectiveBuilder, MarkupLanguage
from sybil_extras.parsers.rest.group_all import GroupAllParser


@pytest.mark.parametrize(
    argnames=("condition", "include_second"),
    argvalues=(
        ("False", True),
        ("True", False),
    ),
)
def test_conditional_skip_grouping(
    *,
    language_directive_builder: tuple[MarkupLanguage, DirectiveBuilder],
    tmp_path: Path,
    condition: str,
    include_second: bool,
) -> None:
    """Only truthy conditional skips exclude the next block from a
    group.
    """
    language, directive_builder = language_directive_builder
    skip_directive = directive_builder(
        directive="skip",
        argument=f"next if({condition})",
    )
    second_block = language.code_block_builder(
        code="second",
        language="python",
    )
    content = language.markup_separator.join(
        [
            language.code_block_builder(code="first", language="python"),
            skip_directive,
            second_block,
        ]
    )
    test_document = tmp_path / "test"
    test_document.write_text(
        data=f"{content}{language.markup_separator}",
        encoding="utf-8",
    )
    evaluator = BlockAccumulatorEvaluator(namespace_key="blocks")
    document = Sybil(
        parsers=[
            language.code_block_parser_cls(
                language="python",
                evaluator=evaluator,
            ),
            language.skip_parser_cls(directive="skip"),
            language.group_all_parser_cls(
                evaluator=evaluator,
                pad_groups=True,
            ),
        ]
    ).parse(path=test_document)

    for example in document.examples():
        with suppress(SkipTest):
            example.evaluate()

    if include_second:
        content_between_blocks = (
            language.markup_separator
            + skip_directive
            + language.markup_separator
        )
        num_newlines_between = content_between_blocks.count("\n")
        padding = "\n" * (num_newlines_between + 2)
        expected = f"first{padding}second\n"
    else:
        expected = "first\n"

    assert document.namespace["blocks"] == [expected]


def test_unconditional_skip_reason_grouping(
    *,
    language_directive_builder: tuple[MarkupLanguage, DirectiveBuilder],
    tmp_path: Path,
) -> None:
    """Non-conditional skip reasons still exclude the next block."""
    language, directive_builder = language_directive_builder
    content = language.markup_separator.join(
        [
            language.code_block_builder(code="first", language="python"),
            directive_builder(directive="skip", argument='next "because"'),
            language.code_block_builder(code="second", language="python"),
        ]
    )
    test_document = tmp_path / "test"
    test_document.write_text(
        data=f"{content}{language.markup_separator}",
        encoding="utf-8",
    )
    evaluator = BlockAccumulatorEvaluator(namespace_key="blocks")
    document = Sybil(
        parsers=[
            language.code_block_parser_cls(
                language="python",
                evaluator=evaluator,
            ),
            language.skip_parser_cls(directive="skip"),
            language.group_all_parser_cls(
                evaluator=evaluator,
                pad_groups=True,
            ),
        ]
    ).parse(path=test_document)

    for example in document.examples():
        with suppress(SkipTest):
            example.evaluate()

    assert document.namespace["blocks"] == ["first\n"]


@pytest.mark.parametrize(
    argnames="parsed",
    argvalues=(
        ("next",),
        (1, None),
        ("unknown", None),
        ("next", object()),
    ),
)
def test_unusual_parsed_markers_do_not_break_grouping(
    *,
    tmp_path: Path,
    parsed: object,
) -> None:
    """Unusual parsed marker shapes do not prevent grouping from finishing."""
    content = """\
.. code-block:: python

   x = 1
"""
    test_document = tmp_path / "test.rst"
    test_document.write_text(data=content, encoding="utf-8")
    evaluator = BlockAccumulatorEvaluator(namespace_key="blocks")

    def custom_parser(document: Document) -> Iterable[Region]:
        """Yield a region with an unusual parsed value."""
        doc_end = len(document.text)
        yield Region(
            start=doc_end - 1,
            end=doc_end,
            parsed=parsed,
            evaluator=NoOpEvaluator(),
            lexemes={},
        )

    document = Sybil(
        parsers=[
            RestCodeBlockParser(
                language="python",
                evaluator=evaluator,
            ),
            custom_parser,
            GroupAllParser(evaluator=evaluator, pad_groups=False),
        ]
    ).parse(path=test_document)

    for example in document.examples():
        example.evaluate()

    assert document.namespace["blocks"] == ["x = 1"]
