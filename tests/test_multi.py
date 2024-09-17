"""Tests for MultiEvaluator."""

from pathlib import Path

import pytest
from sybil import Example, Sybil
from sybil.parsers.rest import CodeBlockParser

from sybil_extras.evaluators.multi import MultiEvaluator


def _evaluator_1(example: Example) -> None:
    """Add `step_1` to namespace."""
    example.namespace["step_1"] = True


def _evaluator_2(example: Example) -> None:
    """Add `step_2` to namespace."""
    example.namespace["step_2"] = True


def _evaluator_3(example: Example) -> None:
    """Add `step_3` to namespace."""
    example.namespace["step_3"] = True


def _failing_evaluator(example: Example) -> None:
    """
    Evaluator that intentionally fails by raising an AssertionError.
    """
    raise AssertionError("Failure in failing_evaluator: " + str(example))


@pytest.fixture(name="rst_file")
def fixture_rst_file(tmp_path: Path) -> Path:
    """
    Fixture to create a temporary RST file with Python code blocks.
    """
    content = """
    .. code-block:: python

        x = 2 + 2
        assert x == 4
    """
    test_document = tmp_path / "test_document.rst"
    test_document.write_text(data=content, encoding="utf-8")
    return test_document


def test_multi_evaluator_runs_all(rst_file: Path) -> None:
    """
    MultiEvaluator runs all given evaluators.
    """
    evaluators = [_evaluator_1, _evaluator_2, _evaluator_3]
    multi_evaluator = MultiEvaluator(evaluators=evaluators)
    parser = CodeBlockParser(language="python", evaluator=multi_evaluator)

    sybil = Sybil(parsers=[parser])

    document = sybil.parse(path=rst_file)
    (example,) = list(document)
    example.evaluate()

    expected_namespace = {"step_1": True, "step_2": True, "step_3": True}
    assert document.namespace == expected_namespace


def test_multi_evaluator_raises_on_failure(rst_file: Path) -> None:
    """
    Test that MultiEvaluator raises an error if an evaluator fails.
    """
    evaluators = [_evaluator_1, _failing_evaluator, _evaluator_3]
    multi_evaluator = MultiEvaluator(evaluators=evaluators)
    parser = CodeBlockParser(language="python", evaluator=multi_evaluator)

    sybil = Sybil(parsers=[parser])

    document = sybil.parse(path=rst_file)
    (example,) = list(document)
    with pytest.raises(AssertionError, match="Failure in failing_evaluator"):
        example.evaluate()
