import os
import textwrap
import uuid
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


def test_pass_env(
    rst_file: Path,
    tmp_path: Path,
) -> None:
    """It is possible to pass environment variables to the command."""
    new_file = tmp_path / "new_file.txt"
    evaluator = ShellCommandEvaluator(
        args=[
            "bash",
            "-c",
            f"echo Hello, $ENV_KEY! > {new_file}; exit 0",
        ],
        env={"ENV_KEY": "ENV_VALUE"},
        pad_file=False,
        write_to_file=False,
    )
    parser = CodeBlockParser(language="python", evaluator=evaluator)
    sybil = Sybil(parsers=[parser])

    document = sybil.parse(path=rst_file)
    (example,) = list(document)
    example.evaluate()
    new_file_content = new_file.read_text(encoding="utf-8")
    assert new_file_content == "Hello, ENV_VALUE!\n"


def test_global_env(
    rst_file: Path,
    tmp_path: Path,
) -> None:
    """Global environment variables are sent to the command by default."""
    env_key = "ENV_" + uuid.uuid4().hex
    os.environ[env_key] = "ENV_VALUE"
    new_file = tmp_path / "new_file.txt"
    evaluator = ShellCommandEvaluator(
        args=[
            "bash",
            "-c",
            f"echo Hello, ${env_key}! > {new_file}; exit 0",
        ],
        pad_file=False,
        write_to_file=False,
    )
    parser = CodeBlockParser(language="python", evaluator=evaluator)
    sybil = Sybil(parsers=[parser])

    document = sybil.parse(path=rst_file)
    (example,) = list(document)
    example.evaluate()
    del os.environ[env_key]
    new_file_content = new_file.read_text(encoding="utf-8")
    assert new_file_content == "Hello, ENV_VALUE!\n"


def test_file_is_passed(
    rst_file: Path,
    tmp_path: Path,
) -> None:
    """A file with the code block content is passed to the command."""
    bash_function = """
    write_to_file() {
        local file="$1"
        local content=`cat $2`
        echo "$content" > "$file"
    }
    write_to_file "$1" "$2"
    """

    file_path = tmp_path / "file.txt"
    evaluator = ShellCommandEvaluator(
        args=["bash", "-c", bash_function, "_", file_path],
        pad_file=False,
        write_to_file=False,
    )
    parser = CodeBlockParser(language="python", evaluator=evaluator)
    sybil = Sybil(parsers=[parser])

    document = sybil.parse(path=rst_file)
    (example,) = list(document)
    example.evaluate()
    expected_content = "x = 2 + 2\nassert x == 4\n"
    assert file_path.read_text(encoding="utf-8") == expected_content


def test_file_path(
    rst_file: Path,
    tmp_path: Path,
) -> None:
    """The given file path is random and absolute, and starts with a name resembling the documentation file name."""
    bash_function = """
    write_to_file() {
        local file="$1"
        local content=$2
        echo "$content" > "$file"
    }
    write_to_file "$1" "$2"
    """

    file_path = tmp_path / "file.txt"
    evaluator = ShellCommandEvaluator(
        args=["bash", "-c", bash_function, "_", file_path],
        pad_file=False,
        write_to_file=False,
    )
    parser = CodeBlockParser(language="python", evaluator=evaluator)
    sybil = Sybil(parsers=[parser])

    document = sybil.parse(path=rst_file)
    (example,) = list(document)
    example.evaluate()
    given_file_path = Path(file_path.read_text(encoding="utf-8").strip())
    assert given_file_path.parent == rst_file.parent
    assert given_file_path.is_absolute()
    assert not given_file_path.exists()
    assert given_file_path.name.startswith("test_document_rst_")
    example.evaluate()
    new_given_file_path = Path(file_path.read_text(encoding="utf-8").strip())
    assert new_given_file_path != given_file_path


# TODO:
# * Test given suffix
# * Test pad
# * Test write to file
