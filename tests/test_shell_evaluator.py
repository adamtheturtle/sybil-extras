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


def test_output_shown_on_error(rst_file: Path) -> None:
    """Stdout and Stderr are shown when a command fails."""
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


def test_no_output_on_success(
    rst_file: Path,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """No output is shown when a command succeeds."""
    new_file = tmp_path / "new_file.txt"
    evaluator = ShellCommandEvaluator(
        args=[
            "bash",
            "-c",
            f"echo 'Hello, Sybil!' > {new_file}",
        ],
        pad_file=False,
        write_to_file=False,
    )
    parser = CodeBlockParser(language="python", evaluator=evaluator)
    sybil = Sybil(parsers=[parser])

    document = sybil.parse(path=rst_file)
    (example,) = list(document)
    example.evaluate()
    new_file_content = new_file.read_text(encoding="utf-8")
    assert new_file_content == "Hello, Sybil!\n"
    outerr = capsys.readouterr()
    assert outerr.out == ""
    assert outerr.err == ""


# def test_shell_command_evaluator_with_environment(rst_file: Path) -> None:
#     """Test that ShellCommandEvaluator respects environment variables."""
#     evaluator = ShellCommandEvaluator(
#         args=["bash", "-c", "echo $TEST_ENV"],
#         env={"TEST_ENV": "SybilTestEnv"},
#         pad_file=False,
#         write_to_file=False,
#     )
#     parser = CodeBlockParser(language="shell", evaluator=evaluator)
#     sybil = Sybil(parsers=[parser])

#     document = sybil.parse(path=rst_file)
#     (example,) = list(document)

#     # Evaluate the shell command
#     example.evaluate()

#     # Check if the environment variable was echoed in the output
#     assert example.namespace["output"] == "SybilTestEnv\n"
