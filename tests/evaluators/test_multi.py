"""
Tests for MultiEvaluator.
"""

from pathlib import Path

import pytest
from sybil import Example, Sybil
from sybil.parsers.rest import CodeBlockParser

from sybil_extras.evaluators.multi import MultiEvaluator


def _evaluator_1(example: Example) -> None:
    """
    Add `step_1` to namespace.
    """
    example.namespace["step_1"] = True


def _evaluator_2(example: Example) -> None:
    """
    Add `step_2` to namespace.
    """
    example.namespace["step_2"] = True


def _evaluator_3(example: Example) -> None:
    """
    Add `step_3` to namespace.
    """
    example.namespace["step_3"] = True


def _failing_evaluator(example: Example) -> None:
    """
    Evaluator that intentionally fails by raising an AssertionError.
    """
    raise AssertionError(
        "Failure in failing_evaluator: " + str(object=example)
    )


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
    (example,) = document.examples()
    example.evaluate()

    expected_namespace = {"step_1": True, "step_2": True, "step_3": True}
    assert document.namespace == expected_namespace


def test_multi_evaluator_raises_on_failure(rst_file: Path) -> None:
    """
    MultiEvaluator raises an error if an evaluator fails.
    """
    evaluators = [_evaluator_1, _failing_evaluator, _evaluator_3]
    multi_evaluator = MultiEvaluator(evaluators=evaluators)
    parser = CodeBlockParser(language="python", evaluator=multi_evaluator)

    sybil = Sybil(parsers=[parser])

    document = sybil.parse(path=rst_file)
    (example,) = document.examples()
    with pytest.raises(
        expected_exception=AssertionError,
        match="Failure in failing_evaluator",
    ):
        example.evaluate()


@pytest.mark.parametrize(
    argnames="failure_string",
    argvalues=["This check failed", ""],
    ids=["non-empty", "empty"],
)
def test_multi_evaluator_propagates_failure_string(
    rst_file: Path,
    failure_string: str,
) -> None:
    """MultiEvaluator propagates failure strings returned by evaluators.

    According to Sybil's API contract, evaluators return Optional[str]
    where:
    - None indicates success
    - A string indicates failure (which Sybil converts to SybilFailure)

    MultiEvaluator must propagate the first failure string encountered,
    including empty strings.
    """

    def _string_returning_evaluator(example: Example) -> str:
        """
        Return a failure string instead of raising an exception.
        """
        del example
        return failure_string

    evaluators = [_evaluator_1, _string_returning_evaluator, _evaluator_3]
    multi_evaluator = MultiEvaluator(evaluators=evaluators)
    parser = CodeBlockParser(language="python", evaluator=multi_evaluator)

    sybil = Sybil(parsers=[parser])

    document = sybil.parse(path=rst_file)
    (example,) = document.examples()
    result = multi_evaluator(example)
    assert result == failure_string
