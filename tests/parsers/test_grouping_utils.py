"""Tests for shared grouping-parser utilities."""

from pathlib import Path

import pytest
from sybil import Sybil

from sybil_extras.evaluators.no_op import NoOpEvaluator
from sybil_extras.languages import DirectiveBuilder, MarkupLanguage
from sybil_extras.parsers.abstract._grouping_utils import (
    count_expected_code_blocks,
)


@pytest.mark.parametrize(
    argnames=("condition", "expected_count"),
    argvalues=(("False", 2), ("True", 1)),
)
def test_conditional_skip_count(
    *,
    language_directive_builder: tuple[MarkupLanguage, DirectiveBuilder],
    tmp_path: Path,
    condition: str,
    expected_count: int,
) -> None:
    """Only truthy conditional skips reduce the expected block count."""
    language, directive_builder = language_directive_builder
    content = language.markup_separator.join(
        [
            language.code_block_builder(code="first", language="python"),
            directive_builder(
                directive="skip",
                argument=f"next if({condition})",
            ),
            language.code_block_builder(code="second", language="python"),
        ]
    )
    test_document = tmp_path / "test"
    test_document.write_text(
        data=f"{content}{language.markup_separator}",
        encoding="utf-8",
    )
    document = Sybil(
        parsers=[
            language.code_block_parser_cls(
                language="python",
                evaluator=NoOpEvaluator(),
            ),
            language.thread_safe_skip_parser_cls(directive="skip"),
        ]
    ).parse(path=test_document)

    assert (
        count_expected_code_blocks(examples=document.examples())
        == expected_count
    )
