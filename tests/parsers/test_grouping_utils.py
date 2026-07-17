"""Tests for shared grouping-parser utilities."""

# pylint: disable=import-private-name,wrong-spelling-in-comment

from pathlib import Path

import pytest
from sybil import Document, Example, Region, Sybil

from sybil_extras.evaluators.no_op import NoOpEvaluator
from sybil_extras.languages import DirectiveBuilder, MarkupLanguage
from sybil_extras.parsers.abstract._grouping_utils import (
    _as_skip_marker,  # pyright: ignore[reportPrivateUsage]
    _skip_condition_is_truthy,  # pyright: ignore[reportPrivateUsage]
    count_expected_code_blocks,
)


def _example(*, parsed: object) -> Example:
    """Build a minimal example for grouping utility tests."""
    return Example(
        document=Document(text="", path="test"),
        line=1,
        column=1,
        region=Region(start=0, end=0, parsed=parsed),
        namespace={},
    )


@pytest.mark.parametrize(
    argnames="reason",
    argvalues=(object(), "because"),
)
def test_unconditional_skip_reason(*, reason: object) -> None:
    """Non-conditional reasons always activate a skip marker."""
    assert _skip_condition_is_truthy(
        example=_example(parsed=("next", reason)),
        reason=reason,
    )


@pytest.mark.parametrize(
    argnames="parsed",
    argvalues=(("next",), (1, None)),
)
def test_invalid_skip_marker_shape(*, parsed: tuple[object, ...]) -> None:
    """Malformed tuples are not treated as skip markers."""
    assert _as_skip_marker(parsed=parsed) is None


def test_unknown_skip_action() -> None:
    """Unknown tuple actions are ignored."""
    assert (
        count_expected_code_blocks(
            examples=[_example(parsed=("unknown", None))]
        )
        == 0
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
