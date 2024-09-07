import textwrap
from pathlib import Path

import pytest
from sybil import Sybil
from sybil.parsers.codeblock import CodeBlockParser

from sybil_extras.evaluators.shell_evaluator import ShellCommandEvaluator


@pytest.fixture(name="rst_file")
def rst_file_fixture(tmp_path: Path) -> Path:
    """
    Fixture to create a temporary RST file with code blocks.
    """
    content = """
    .. code-block:: python

        x = 2 + 2
        assert x == 4
    """
    test_document = tmp_path / "test_document.rst"
    test_document.write_text(data=content, encoding="utf-8")
    return test_document


def test_shell_command_evaluator_runs(rst_file: Path) -> None:
    """Test that ShellCommandEvaluator successfully runs a shell command."""
    evaluator = ShellCommandEvaluator(
        args=[
            "bash",
            "-c",
            "echo 'Hello, Sybil!'; echo >&2 'Hello Stderr!'; exit 1",
        ],
        pad_file=False,
        write_to_file=False,
    )
    parser = CodeBlockParser(language="python", evaluator=evaluator)
    sybil = Sybil(parsers=[parser])

    document = sybil.parse(path=rst_file)
    (example,) = list(document)

    expected_output = textwrap.dedent(
        text="""\
        Shell command failed:
        Command: bash -c 'echo '"'"'Hello, Sybil!'"'"'; echo >&2 '"'"'Hello Stderr!'"'"'; exit 1'
        Output: Hello, Sybil!

        Error: Hello Stderr!
        """,
    )

    with pytest.raises(expected_exception=ValueError, match=expected_output):
        example.evaluate()


def test_shell_command_evaluator_with_failure(rst_file: Path) -> None:
    """Test that ShellCommandEvaluator handles a failing command."""
    evaluator = ShellCommandEvaluator(
        args=["bash", "-c", "exit 1"], pad_file=False, write_to_file=False
    )
    parser = CodeBlockParser(language="shell", evaluator=evaluator)
    sybil = Sybil(parsers=[parser])

    document = sybil.parse(path=rst_file)
    (example,) = list(document)

    # Expecting an error to be raised due to the command failure
    with pytest.raises(subprocess.CalledProcessError):
        example.evaluate()


def test_shell_command_evaluator_with_environment(rst_file: Path) -> None:
    """Test that ShellCommandEvaluator respects environment variables."""
    evaluator = ShellCommandEvaluator(
        args=["bash", "-c", "echo $TEST_ENV"],
        env={"TEST_ENV": "SybilTestEnv"},
        pad_file=False,
        write_to_file=False,
    )
    parser = CodeBlockParser(language="shell", evaluator=evaluator)
    sybil = Sybil(parsers=[parser])

    document = sybil.parse(path=rst_file)
    (example,) = list(document)

    # Evaluate the shell command
    example.evaluate()

    # Check if the environment variable was echoed in the output
    assert example.namespace["output"] == "SybilTestEnv\n"
