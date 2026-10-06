"""Document lifetime and native skip translation."""

from pathlib import Path
from unittest import SkipTest

import karva
import pytest
from sybil import Example, Sybil
from sybil.parsers.rest import CodeBlockParser, DocTestParser

from sybil_extras.integrations._karva_runtime import DocumentTests


def test_namespace_and_lifecycle(*, tmp_path: Path) -> None:
    """Run document callbacks once with the shared, updated namespace."""
    events: list[str] = []

    def setup(namespace: dict[str, object]) -> None:
        """Seed this document's namespace."""
        namespace["value"] = "from setup"
        events.append("setup")

    def teardown(namespace: dict[str, object]) -> None:
        """Observe the example's final state."""
        assert namespace["value"] == "from fixture"
        events.append("teardown")

    path = tmp_path / "example.rst"
    _ = path.write_text(
        data='>>> assert value == "from fixture"\n', encoding="utf-8"
    )
    suite = DocumentTests(
        sybil=Sybil(parsers=[DocTestParser()], setup=setup, teardown=teardown),
        path=path,
    )
    (example,) = suite.examples
    with suite.lifecycle() as active:
        assert active is suite
        suite.evaluate(example=example, fixtures={"value": "from fixture"})
    assert events == ["setup", "teardown"]


def test_cleanup_after_failure(*, tmp_path: Path) -> None:
    """Run cleanup when example evaluation raises."""
    events: list[str] = []

    def teardown(namespace: dict[str, object]) -> None:
        """Record cleanup."""
        del namespace
        events.append("teardown")

    path = tmp_path / "example.rst"
    _ = path.write_text(
        data=".. code-block:: python\n\n    pass\n",
        encoding="utf-8",
    )
    suite = DocumentTests(
        sybil=Sybil(
            parsers=[CodeBlockParser(language="python", evaluator=_fail)],
            teardown=teardown,
        ),
        path=path,
    )
    (example,) = suite.examples
    with (
        pytest.raises(expected_exception=ValueError, match="example failed"),
        suite.lifecycle(),
    ):
        suite.evaluate(example=example, fixtures={})
    assert events == ["teardown"]


def _fail(example: Example) -> None:
    """Raise a real evaluator error."""
    del example
    message = "example failed"
    raise ValueError(message)


def _skip(example: Example) -> None:
    """Raise the exception used by Sybil's skip evaluators."""
    del example
    message = "skipped example"
    raise SkipTest(message)


def test_native_skip(*, tmp_path: Path) -> None:
    """Convert Sybil's skip to a native Karva outcome."""
    path = tmp_path / "example.rst"
    _ = path.write_text(
        data=".. code-block:: python\n\n    pass\n", encoding="utf-8"
    )
    suite = DocumentTests(
        sybil=Sybil(
            parsers=[CodeBlockParser(language="python", evaluator=_skip)]
        ),
        path=path,
    )
    (example,) = suite.examples
    with (
        suite.lifecycle(),
        pytest.raises(
            expected_exception=karva.SkipError, match="skipped example"
        ),
    ):
        suite.evaluate(example=example, fixtures={})
