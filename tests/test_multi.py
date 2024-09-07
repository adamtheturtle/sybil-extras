import pytest
from sybil import Example

from sybil_extras.evaluators.multi import (
    MultiEvaluator,  # Import your MultiEvaluator class
)


# 1. Simple evaluator that verifies the result of an expression
def evaluator1(example: Example) -> None:
    # For simplicity, we'll assume the example's source can be evaluated directly
    result = eval(example.source)
    assert result == example.expected, f"Expected {example.expected}, got {result}"


# 2. Another evaluator that just logs the evaluation step by adding it to the namespace
def evaluator2(example: Example) -> None:
    example.namespace["evaluated"] = True  # Set a flag in the example's namespace


# 3. Test that MultiEvaluator runs all evaluators correctly
def test_multi_evaluator_runs_all():
    # Mock example
    example = Example(
        location=None,
        document=None,
        source="2 + 2",
        namespace={},
        expected=4  # Expecting result 4
    )

    # Create MultiEvaluator with both evaluators
    multi_evaluator = MultiEvaluator([evaluator1, evaluator2])

    # Call MultiEvaluator
    multi_evaluator(example)

    # Check if evaluator2 modified the namespace
    assert example.namespace["evaluated"], "evaluator2 did not run correctly"


# 4. Test that MultiEvaluator raises an error if one evaluator fails
def test_multi_evaluator_raises_on_failure():
    # Mock example
    example = Example(
        location=None,
        document=None,
        source="2 + 2",
        namespace={},
        expected=5  # Intentionally incorrect expectation to cause failure
    )

    # Create MultiEvaluator with both evaluators
    multi_evaluator = MultiEvaluator([evaluator1, evaluator2])

    # Assert that MultiEvaluator raises AssertionError when evaluator1 fails
    with pytest.raises(AssertionError, match="Expected 5, got 4"):
        multi_evaluator(example)


# 5. Test that MultiEvaluator runs no evaluators if the list is empty
def test_multi_evaluator_no_evaluators():
    # Mock example
    example = Example(
        location=None,
        document=None,
        source="2 + 2",
        namespace={},
        expected=4
    )

    # Create MultiEvaluator with no evaluators
    multi_evaluator = MultiEvaluator([])

    # Call MultiEvaluator, expecting no errors and no changes to the example
    multi_evaluator(example)

    # Ensure the namespace is still empty
    assert "evaluated" not in example.namespace, "Namespace should remain unchanged"


# 6. Test with multiple successful evaluators in sequence
def test_multi_evaluator_multiple_successful_evaluators():
    # Another evaluator that also modifies the namespace
    def evaluator3(example: Example) -> None:
        example.namespace["step"] = 3  # Set an arbitrary value in the namespace

    # Mock example
    example = Example(
        location=None,
        document=None,
        source="sum([i for i in range(5)])",  # 0 + 1 + 2 + 3 + 4
        namespace={},
        expected=10  # Expected result is 10
    )

    # Create MultiEvaluator instance with all three evaluators
    multi_evaluator = MultiEvaluator([evaluator1, evaluator2, evaluator3])

    # Call MultiEvaluator
    multi_evaluator(example)

    # Check if both evaluators modified the namespace correctly
    assert example.namespace["evaluated"], "evaluator2 did not run"
    assert example.namespace["step"] == 3, "evaluator3 did not modify the namespace"


# 7. Test if evaluators receive the same example and modifications persist
def test_multi_evaluator_propagates_example():
    # Evaluator that modifies the example in the first step
    def evaluator3(example: Example) -> None:
        example.namespace["step"] = 1

    # Evaluator that checks the modification and modifies it further
    def evaluator4(example: Example) -> None:
        assert example.namespace["step"] == 1, "evaluator3 did not set 'step' correctly"
        example.namespace["step"] = 2

    example = Example(
        location=None,
        document=None,
        source="2 + 2",
        namespace={},
        expected=4
    )

    # Create MultiEvaluator instance with both evaluators
    multi_evaluator = MultiEvaluator([evaluator3, evaluator4])

    # Call MultiEvaluator
    multi_evaluator(example)

    # Assert that the second evaluator received the modified example
    assert example.namespace["step"] == 2, "Evaluator chain did not propagate modifications"


# 8. Test with MultiEvaluator integrated with Sybil (assuming you have Sybil test cases)
def test_sybil_integration_with_multi_evaluator():
    from sybil import Sybil
    from sybil.parsers.doctest import DocTestParser

    # Setup the MultiEvaluator with the simple evaluators
    multi_evaluator = MultiEvaluator([evaluator1, evaluator2])

    # Set up Sybil with a mock document directory and the MultiEvaluator
    suite = Sybil(
        [DocTestParser()],
        evaluators=[multi_evaluator],
        paths=["tests/mock_docs"]  # Use a directory containing mock documentation
    )

    # Run the test suite and assert that it runs successfully
    result = suite.run(globals())
    assert result.wasSuccessful(), "Sybil test suite failed"
