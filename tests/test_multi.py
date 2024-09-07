"""Tests for MultiEvaluator."""

from pathlib import Path

import pytest
from sybil import Example, Sybil
from sybil.parsers.rest import CodeBlockParser

from sybil_extras.evaluators.multi import MultiEvaluator


def _evaluator_1(example: Example) -> None:
    example.namespace["step_1"] = True


def _evaluator_2(example: Example) -> None:
    example.namespace["step_2"] = True


def _evaluator_3(example: Example) -> None:
    example.namespace["step_3"] = True


def _failing_evaluator(example: Example) -> None:
    """
    Evaluator that intentionally fails by raising an AssertionError.
    """
    raise AssertionError("Failure in failing_evaluator: " + str(example))

@pytest.fixture(name="rst_file")
def rst_file_fixture(tmp_path: Path) -> Path:
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
    (example, ) = list(document)
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
    (example, ) = list(document)
    with pytest.raises(AssertionError, match="Failure in failing_evaluator"):
        example.evaluate()


def test_multi_evaluator_no_evaluators(rst_file: Path) -> None:
    """
    Test that MultiEvaluator runs without error when no evaluators are provided.
    """
    # Create MultiEvaluator with no evaluators
    multi_evaluator = MultiEvaluator(evaluators=[])

    # Setup Sybil with the CodeBlockParser
    suite = Sybil(
        parsers=[CodeBlockParser(language="python", evaluator=multi_evaluator)],

    )

    # Run the Sybil test suite
    result = suite.parse(path=rst_file)

    # Ensure the test suite passes with no evaluators
    assert result.wasSuccessful(), "Sybil test suite should have passed with no evaluators"


def test_multi_evaluator_propagates_example(rst_file: Path) -> None:
    """
    Test that modifications made by one evaluator are visible to subsequent evaluators.
    """

    # Evaluator that modifies the namespace
    def evaluator_4(example: Example) -> None:
        """
        Evaluator 4 sets 'step_4' in the namespace.
        """
        example.namespace["step_4"] = True

    def evaluator_5(example: Example) -> None:
        """
        Evaluator 5 checks if 'step_4' is set and sets 'step_5' in the namespace.
        """
        assert example.namespace.get("step_4"), "evaluator_4 did not set 'step_4'"
        example.namespace["step_5"] = True

    # Create MultiEvaluator with evaluators 4 and 5
    multi_evaluator = MultiEvaluator(evaluators=[evaluator_4, evaluator_5])

    # Setup Sybil with the CodeBlockParser
    suite = Sybil(
        parsers=[CodeBlockParser(language="python", evaluator=multi_evaluator)],

    )

    # Run the Sybil test suite
    result = suite.parse(path=rst_file)

    # Ensure the test suite passes
    assert result.wasSuccessful(), "Sybil test suite should have passed with propagating evaluators"

    # Create an example and check namespace propagation
    example = Example(location=None, document=None, source="x = 2 + 2", namespace={}, expected=None)
    multi_evaluator(example=example)

    assert example.namespace["step_4"], "'step_4' not set by evaluator_4"
    assert example.namespace["step_5"], "'step_5' not set by evaluator_5"
