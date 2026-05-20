"""Tests for the thread-safe skip parser shared across markup
languages.
"""

import threading
from collections.abc import Iterable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, cast  # noqa: TID251
from unittest import SkipTest

import pytest
from sybil import Document, Example, Region, Sybil
from sybil.evaluators.python import PythonEvaluator
from sybil.typing import Evaluator

from sybil_extras.evaluators.thread_safe_skip import ThreadSafeSkipper
from sybil_extras.languages import DirectiveBuilder, MarkupLanguage


class _ThreadSafeSkipParserProtocol(Protocol):
    """Minimal shape of a thread-safe skip parser used in these tests."""

    def __init__(self, directive: str) -> None:
        """Construct a skip parser for ``directive``."""
        ...  # pylint: disable=unnecessary-ellipsis

    def __call__(self, document: Document) -> Iterable[Region]:
        """Yield skip regions for ``document``."""
        ...  # pylint: disable=unnecessary-ellipsis

    def get_skipper(self) -> ThreadSafeSkipper:
        """Return the thread-safe skipper backing this parser."""
        ...  # pylint: disable=unnecessary-ellipsis


@dataclass(frozen=True)
class _SybilFixture:
    """Bundle of a configured ``Sybil`` and its thread-safe skip
    parser.
    """

    sybil: Sybil
    skip_parser: _ThreadSafeSkipParserProtocol


class _RecordingEvaluator:
    """A thread-safe code-block evaluator that records the regions it
    ran.
    """

    def __init__(self) -> None:
        """Initialize the recorder with an empty evaluation list."""
        self.evaluated: list[int] = []
        self._lock = threading.Lock()

    def __call__(self, example: Example) -> None:
        """Record that ``example`` was evaluated."""
        with self._lock:
            self.evaluated.append(example.region.start)


def _build_sybil(
    *,
    language: MarkupLanguage,
    directive_name: str,
    code_block_evaluator: Evaluator,
) -> _SybilFixture:
    """Build a Sybil instance with the thread-safe skip parser
    configured.
    """
    skip_parser = cast(  # noqa: TID251
        "_ThreadSafeSkipParserProtocol",
        language.thread_safe_skip_parser_cls(directive=directive_name),
    )
    code_block_parser = language.code_block_parser_cls(
        language="python",
        evaluator=code_block_evaluator,
    )
    sybil = Sybil(parsers=[code_block_parser, skip_parser])
    return _SybilFixture(sybil=sybil, skip_parser=skip_parser)


def test_skip_next_sequential(
    *,
    language_directive_builder: tuple[MarkupLanguage, DirectiveBuilder],
    tmp_path: Path,
) -> None:
    """``skip: next`` skips a single example when run sequentially."""
    language, directive_builder = language_directive_builder
    content = language.markup_separator.join(
        [
            language.code_block_builder(code="x = []", language="python"),
            directive_builder(directive="custom-skip", argument="next"),
            language.code_block_builder(code="x = [*x, 2]", language="python"),
            language.code_block_builder(code="x = [*x, 3]", language="python"),
        ]
    )
    test_document = tmp_path / "test"
    test_document.write_text(
        data=f"{content}{language.markup_separator}",
        encoding="utf-8",
    )
    fixture = _build_sybil(
        language=language,
        directive_name="custom-skip",
        code_block_evaluator=PythonEvaluator(),
    )
    document = fixture.sybil.parse(path=test_document)
    for example in document.examples():
        example.evaluate()
    assert document.namespace["x"] == [3]


def test_skip_start_end_sequential(
    *,
    language_directive_builder: tuple[MarkupLanguage, DirectiveBuilder],
    tmp_path: Path,
) -> None:
    """``skip: start`` / ``skip: end`` skips an interval of examples."""
    language, directive_builder = language_directive_builder
    content = language.markup_separator.join(
        [
            language.code_block_builder(code="x = [1]", language="python"),
            directive_builder(directive="custom-skip", argument="start"),
            language.code_block_builder(code="x = [*x, 2]", language="python"),
            language.code_block_builder(code="x = [*x, 3]", language="python"),
            directive_builder(directive="custom-skip", argument="end"),
            language.code_block_builder(code="x = [*x, 4]", language="python"),
        ]
    )
    test_document = tmp_path / "test"
    test_document.write_text(
        data=f"{content}{language.markup_separator}",
        encoding="utf-8",
    )
    fixture = _build_sybil(
        language=language,
        directive_name="custom-skip",
        code_block_evaluator=PythonEvaluator(),
    )
    document = fixture.sybil.parse(path=test_document)
    for example in document.examples():
        example.evaluate()
    assert document.namespace["x"] == [1, 4]


def test_skip_next_with_reason(
    *,
    language_directive_builder: tuple[MarkupLanguage, DirectiveBuilder],
    tmp_path: Path,
) -> None:
    """An unconditional reason raises ``SkipTest`` for the next
    example.
    """
    language, directive_builder = language_directive_builder
    content = language.markup_separator.join(
        [
            directive_builder(
                directive="custom-skip", argument='next "always"'
            ),
            language.code_block_builder(code="x = 1", language="python"),
        ]
    )
    test_document = tmp_path / "test"
    test_document.write_text(
        data=f"{content}{language.markup_separator}",
        encoding="utf-8",
    )
    fixture = _build_sybil(
        language=language,
        directive_name="custom-skip",
        code_block_evaluator=PythonEvaluator(),
    )
    document = fixture.sybil.parse(path=test_document)
    examples = list(document.examples())
    examples[0].evaluate()
    with pytest.raises(expected_exception=SkipTest, match="always"):
        examples[1].evaluate()


def test_skip_next_conditional_truthy(
    *,
    language_directive_builder: tuple[MarkupLanguage, DirectiveBuilder],
    tmp_path: Path,
) -> None:
    """A truthy ``if(...)`` reason skips with a ``SkipTest`` exception."""
    language, directive_builder = language_directive_builder
    content = language.markup_separator.join(
        [
            directive_builder(
                directive="custom-skip", argument="next if(True)"
            ),
            language.code_block_builder(code="x = 1", language="python"),
        ]
    )
    test_document = tmp_path / "test"
    test_document.write_text(
        data=f"{content}{language.markup_separator}",
        encoding="utf-8",
    )
    fixture = _build_sybil(
        language=language,
        directive_name="custom-skip",
        code_block_evaluator=PythonEvaluator(),
    )
    document = fixture.sybil.parse(path=test_document)
    examples = list(document.examples())
    examples[0].evaluate()
    with pytest.raises(expected_exception=SkipTest):
        examples[1].evaluate()


def test_skip_next_conditional_falsy(
    *,
    language_directive_builder: tuple[MarkupLanguage, DirectiveBuilder],
    tmp_path: Path,
) -> None:
    """A falsy ``if(...)`` reason lets the next example run normally."""
    language, directive_builder = language_directive_builder
    content = language.markup_separator.join(
        [
            directive_builder(
                directive="custom-skip", argument="next if(False)"
            ),
            language.code_block_builder(code="x = 1", language="python"),
        ]
    )
    test_document = tmp_path / "test"
    test_document.write_text(
        data=f"{content}{language.markup_separator}",
        encoding="utf-8",
    )
    fixture = _build_sybil(
        language=language,
        directive_name="custom-skip",
        code_block_evaluator=PythonEvaluator(),
    )
    document = fixture.sybil.parse(path=test_document)
    for example in document.examples():
        example.evaluate()
    assert document.namespace["x"] == 1


def test_concurrent_evaluation_deterministic(
    *,
    language_directive_builder: tuple[MarkupLanguage, DirectiveBuilder],
    tmp_path: Path,
) -> None:
    """Concurrent evaluation yields the same result as sequential.

    Reproduces https://github.com/simplistix/sybil/issues/166: a
    document containing a ``skip: start`` / ``skip: end`` interval is
    evaluated by a :class:`ThreadPoolExecutor` many times. With the
    upstream ``Skipper``, decisions race and the namespace becomes
    non-deterministic. With :class:`ThreadSafeSkipper`, every iteration
    matches the sequential result.
    """
    language, directive_builder = language_directive_builder
    content = language.markup_separator.join(
        [
            language.code_block_builder(code="a = 1", language="python"),
            directive_builder(directive="custom-skip", argument="start"),
            language.code_block_builder(code="b = 1", language="python"),
            language.code_block_builder(code="c = 1", language="python"),
            directive_builder(directive="custom-skip", argument="end"),
            language.code_block_builder(code="d = 1", language="python"),
        ]
    )
    test_document = tmp_path / "test"
    test_document.write_text(
        data=f"{content}{language.markup_separator}",
        encoding="utf-8",
    )

    for _ in range(50):
        recorder = _RecordingEvaluator()
        fixture = _build_sybil(
            language=language,
            directive_name="custom-skip",
            code_block_evaluator=recorder,
        )
        document = fixture.sybil.parse(path=test_document)
        examples: list[Example] = list(document.examples())
        first_code, _start, second_code, third_code, _end, fourth_code = (
            examples
        )

        def evaluate(ex: Example) -> None:
            """Evaluate ``ex``."""
            ex.evaluate()

        with ThreadPoolExecutor(max_workers=8) as executor:
            list(executor.map(evaluate, examples))

        assert sorted(recorder.evaluated) == sorted(
            [first_code.region.start, fourth_code.region.start],
        )
        assert second_code.region.start not in recorder.evaluated
        assert third_code.region.start not in recorder.evaluated


def test_concurrent_skip_next(
    *,
    language_directive_builder: tuple[MarkupLanguage, DirectiveBuilder],
    tmp_path: Path,
) -> None:
    """Concurrent evaluation handles ``skip: next`` deterministically."""
    language, directive_builder = language_directive_builder
    content = language.markup_separator.join(
        [
            language.code_block_builder(code="a = 1", language="python"),
            directive_builder(directive="custom-skip", argument="next"),
            language.code_block_builder(code="b = 1", language="python"),
            language.code_block_builder(code="c = 1", language="python"),
        ]
    )
    test_document = tmp_path / "test"
    test_document.write_text(
        data=f"{content}{language.markup_separator}",
        encoding="utf-8",
    )

    for _ in range(50):
        recorder = _RecordingEvaluator()
        fixture = _build_sybil(
            language=language,
            directive_name="custom-skip",
            code_block_evaluator=recorder,
        )
        document = fixture.sybil.parse(path=test_document)
        examples: list[Example] = list(document.examples())
        first_code, _skip_next, skipped_code, third_code = examples

        def evaluate(ex: Example) -> None:
            """Evaluate ``ex``."""
            ex.evaluate()

        with ThreadPoolExecutor(max_workers=8) as executor:
            list(executor.map(evaluate, examples))

        assert sorted(recorder.evaluated) == sorted(
            [first_code.region.start, third_code.region.start],
        )
        assert skipped_code.region.start not in recorder.evaluated


def test_sequence_error_directive_name(
    *,
    language_directive_builder: tuple[MarkupLanguage, DirectiveBuilder],
    tmp_path: Path,
) -> None:
    """``skip: end`` without ``start`` raises with the directive name."""
    language, directive_builder = language_directive_builder
    content = directive_builder(directive="custom-skip", argument="end")
    test_document = tmp_path / "test"
    test_document.write_text(
        data=f"{content}{language.markup_separator}",
        encoding="utf-8",
    )
    fixture = _build_sybil(
        language=language,
        directive_name="custom-skip",
        code_block_evaluator=PythonEvaluator(),
    )
    document = fixture.sybil.parse(path=test_document)
    (example,) = document.examples()
    with pytest.raises(
        expected_exception=ValueError,
        match="'custom-skip: end' must follow 'custom-skip: start'",
    ):
        example.evaluate()


def test_sequence_error_bad_action(
    *,
    language_directive_builder: tuple[MarkupLanguage, DirectiveBuilder],
    tmp_path: Path,
) -> None:
    """An unknown action raises ``ValueError`` when its directive runs."""
    language, directive_builder = language_directive_builder
    content = directive_builder(directive="custom-skip", argument="bogus")
    test_document = tmp_path / "test"
    test_document.write_text(
        data=f"{content}{language.markup_separator}",
        encoding="utf-8",
    )
    fixture = _build_sybil(
        language=language,
        directive_name="custom-skip",
        code_block_evaluator=PythonEvaluator(),
    )
    document = fixture.sybil.parse(path=test_document)
    (example,) = document.examples()
    with pytest.raises(
        expected_exception=ValueError,
        match="Bad skip action: bogus",
    ):
        example.evaluate()


def test_sequence_error_double_start(
    *,
    language_directive_builder: tuple[MarkupLanguage, DirectiveBuilder],
    tmp_path: Path,
) -> None:
    """A second ``start`` after another ``start`` raises
    ``ValueError``.
    """
    language, directive_builder = language_directive_builder
    content = language.markup_separator.join(
        [
            directive_builder(directive="custom-skip", argument="start"),
            directive_builder(directive="custom-skip", argument="start"),
        ]
    )
    test_document = tmp_path / "test"
    test_document.write_text(
        data=f"{content}{language.markup_separator}",
        encoding="utf-8",
    )
    fixture = _build_sybil(
        language=language,
        directive_name="custom-skip",
        code_block_evaluator=PythonEvaluator(),
    )
    document = fixture.sybil.parse(path=test_document)
    examples = list(document.examples())
    examples[0].evaluate()
    with pytest.raises(
        expected_exception=ValueError,
        match="'custom-skip: start' cannot follow 'custom-skip: start'",
    ):
        examples[1].evaluate()


def test_sequence_error_end_with_reason(
    *,
    language_directive_builder: tuple[MarkupLanguage, DirectiveBuilder],
    tmp_path: Path,
) -> None:
    """``skip: end <reason>`` raises ``ValueError`` when its directive
    runs.
    """
    language, directive_builder = language_directive_builder
    content = language.markup_separator.join(
        [
            directive_builder(directive="custom-skip", argument="start"),
            directive_builder(directive="custom-skip", argument='end "nope"'),
        ]
    )
    test_document = tmp_path / "test"
    test_document.write_text(
        data=f"{content}{language.markup_separator}",
        encoding="utf-8",
    )
    fixture = _build_sybil(
        language=language,
        directive_name="custom-skip",
        code_block_evaluator=PythonEvaluator(),
    )
    document = fixture.sybil.parse(path=test_document)
    examples = list(document.examples())
    examples[0].evaluate()
    with pytest.raises(
        expected_exception=ValueError,
        match="Cannot have condition on 'skip: end'",
    ):
        examples[1].evaluate()


def test_multiple_intervals_in_one_document(
    *,
    language_directive_builder: tuple[MarkupLanguage, DirectiveBuilder],
    tmp_path: Path,
) -> None:
    """A document can contain multiple ``start``/``end`` intervals."""
    language, directive_builder = language_directive_builder
    content = language.markup_separator.join(
        [
            language.code_block_builder(code="a = 1", language="python"),
            directive_builder(directive="custom-skip", argument="start"),
            language.code_block_builder(code="b = 1", language="python"),
            directive_builder(directive="custom-skip", argument="end"),
            language.code_block_builder(code="c = 1", language="python"),
            directive_builder(directive="custom-skip", argument="start"),
            language.code_block_builder(code="d = 1", language="python"),
            directive_builder(directive="custom-skip", argument="end"),
            language.code_block_builder(code="e = 1", language="python"),
        ]
    )
    test_document = tmp_path / "test"
    test_document.write_text(
        data=f"{content}{language.markup_separator}",
        encoding="utf-8",
    )
    fixture = _build_sybil(
        language=language,
        directive_name="custom-skip",
        code_block_evaluator=PythonEvaluator(),
    )
    document = fixture.sybil.parse(path=test_document)
    for example in document.examples():
        example.evaluate()
    assert "a" in document.namespace
    assert "c" in document.namespace
    assert "e" in document.namespace
    assert "b" not in document.namespace
    assert "d" not in document.namespace


def test_end_cancels_pending_next(
    *,
    language_directive_builder: tuple[MarkupLanguage, DirectiveBuilder],
    tmp_path: Path,
) -> None:
    """``skip: end`` cancels an unconsumed ``skip: next``.

    Mirrors upstream ``Skipper.remove`` clearing per-document state:
    the example after ``end`` should run normally rather than being
    treated as the target of the prior ``next``.
    """
    language, directive_builder = language_directive_builder
    content = language.markup_separator.join(
        [
            directive_builder(directive="custom-skip", argument="next"),
            directive_builder(directive="custom-skip", argument="end"),
            language.code_block_builder(code="a = 1", language="python"),
        ]
    )
    test_document = tmp_path / "test"
    test_document.write_text(
        data=f"{content}{language.markup_separator}",
        encoding="utf-8",
    )
    fixture = _build_sybil(
        language=language,
        directive_name="custom-skip",
        code_block_evaluator=PythonEvaluator(),
    )
    document = fixture.sybil.parse(path=test_document)
    for example in document.examples():
        example.evaluate()
    assert document.namespace["a"] == 1


def test_no_skip_directives(
    *,
    language_directive_builder: tuple[MarkupLanguage, DirectiveBuilder],
    tmp_path: Path,
) -> None:
    """A document without any skip directives evaluates normally."""
    language, _ = language_directive_builder
    content = language.code_block_builder(code="a = 1", language="python")
    test_document = tmp_path / "test"
    test_document.write_text(
        data=f"{content}{language.markup_separator}",
        encoding="utf-8",
    )
    fixture = _build_sybil(
        language=language,
        directive_name="custom-skip",
        code_block_evaluator=PythonEvaluator(),
    )
    document = fixture.sybil.parse(path=test_document)
    for example in document.examples():
        example.evaluate()
    assert document.namespace["a"] == 1


def test_get_skipper_returns_thread_safe(
    *,
    language_directive_builder: tuple[MarkupLanguage, DirectiveBuilder],
) -> None:
    """``get_skipper()`` returns the ``ThreadSafeSkipper`` instance."""
    language, _ = language_directive_builder
    parser = language.thread_safe_skip_parser_cls(directive="custom-skip")
    skipper = parser.get_skipper()
    assert isinstance(skipper, ThreadSafeSkipper)
