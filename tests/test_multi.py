from pathlib import Path

import pytest
from sybil import Example, Sybil
from sybil.parsers.rest import CodeBlockParser

from sybil_extras.evaluators.multi import MultiEvaluator


# 1. Evaluator that adds a 'step_1' flag to the namespace
def evaluator_1(example: Example) -> None:
    """
    Evaluator 1 modifies the example's namespace by setting 'step_1' to True.
    """
    breakpoint()
    example.namespace["step_1"] = True


# 2. Evaluator that adds a 'step_2' flag to the namespace
def evaluator_2(example: Example) -> None:
    """
    Evaluator 2 modifies the example's namespace by setting 'step_2' to True.
    """
    example.namespace["step_2"] = True


# 3. Evaluator that adds a 'step_3' flag to the namespace
def evaluator_3(example: Example) -> None:
    """
    Evaluator 3 modifies the example's namespace by setting 'step_3' to True.
    """
    example.namespace["step_3"] = True


@pytest.fixture
def rst_file(tmp_path: Path) -> Path:
    """
    Fixture to create a temporary RST file with Python code blocks.
    """
    content = """
    .. code-block:: python

        x = 2 + 2
        assert x == 4

    .. code-block:: python

        y = sum([i for i in range(5)])
        assert y == 10
    """
    rst_file = tmp_path / "test_document.rst"
    rst_file.write_text(content)
    return rst_file


def test_multi_evaluator_runs_all(rst_file: Path) -> None:
    """
    Test that MultiEvaluator runs all evaluators and modifies the namespace as expected.
    """
    # Create a MultiEvaluator with three evaluators
    multi_evaluator = MultiEvaluator(evaluators=[evaluator_1, evaluator_2, evaluator_3])

    # Setup Sybil with the CodeBlockParser, passing the MultiEvaluator
    suite = Sybil(
        parsers=[CodeBlockParser(language="python", evaluator=multi_evaluator)],

    )

    # Run the Sybil test suite
    result = suite.parse(path=rst_file)
    breakpoint()

    # # Check that the evaluators modified the namespace correctly
    # example = Example(location=None, document=None, source="x = 2 + 2", namespace={}, expected=None)
    # multi_evaluator(example=example)

    # assert result.wasSuccessful(), "Sybil test suite did not pass"
    # assert example.namespace["step_1"], "'step_1' not set by evaluator_1"
    # assert example.namespace["step_2"], "'step_2' not set by evaluator_2"
    # assert example.namespace["step_3"], "'step_3' not set by evaluator_3"


def test_multi_evaluator_raises_on_failure(rst_file: Path) -> None:
    """
    Test that MultiEvaluator raises an error if an evaluator fails.
    """

    # Create a failing evaluator that raises an AssertionError
    def failing_evaluator(example: Example) -> None:
        """
        Evaluator that intentionally fails by raising an AssertionError.
        """
        raise AssertionError("Failure in failing_evaluator")

    # Create MultiEvaluator with one failing evaluator and two successful ones
    multi_evaluator = MultiEvaluator(evaluators=[evaluator_1, failing_evaluator, evaluator_3])

    # Setup Sybil with the CodeBlockParser
    suite = Sybil(
        parsers=[CodeBlockParser(language="python", evaluator=multi_evaluator)],

    )

    # Ensure that MultiEvaluator raises an AssertionError
    with pytest.raises(AssertionError, match="Failure in failing_evaluator"):
        result = suite.parse(path=rst_file)
        assert not result.wasSuccessful(), "Sybil test suite should have failed"


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
