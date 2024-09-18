"""Tests for the ShellCommandEvaluator"""

import os
import stat
import subprocess
import textwrap
from pathlib import Path

import pytest
from sybil import Sybil
from sybil.parsers.codeblock import CodeBlockParser

from sybil_extras.evaluators.shell_evaluator import ShellCommandEvaluator


@pytest.fixture(name="rst_file")
def fixture_rst_file(tmp_path: Path) -> Path:
    """
    Fixture to create a temporary RST file with code blocks.
    """
    # Relied upon features:
    #
    # * Includes exactly one code block
    # * Contents of the code block match those in tests
    # * The code block is the last element in the file
    # * There is text outside the code block
    content = textwrap.dedent(
        text="""\
        Not in code block

        .. code-block:: python

           x = 2 + 2
           assert x == 4
        """
    )
    test_document = tmp_path / "test_document.example.rst"
    test_document.write_text(data=content, encoding="utf-8")
    return test_document


def test_error(rst_file: Path) -> None:
    """
    A ``subprocess.CalledProcessError`` is raised if the command fails.
    """
    args = ["sh", "-c", "exit 1"]
    evaluator = ShellCommandEvaluator(
        args=args,
        pad_file=False,
        write_to_file=False,
    )
    parser = CodeBlockParser(language="python", evaluator=evaluator)
    sybil = Sybil(parsers=[parser])

    document = sybil.parse(path=rst_file)
    (example,) = list(document)

    with pytest.raises(
        expected_exception=subprocess.CalledProcessError
    ) as exc:
        example.evaluate()

    assert exc.value.returncode == 1
    # The last element is the path to the temporary file.
    assert exc.value.cmd[:-1] == args


def test_output_shown(
    rst_file: Path,
    capfd: pytest.CaptureFixture[str],
) -> None:
    """Output is shown."""
    evaluator = ShellCommandEvaluator(
        args=[
            "sh",
            "-c",
            "echo 'Hello, Sybil!' && echo >&2 'Hello Stderr!'",
        ],
        pad_file=False,
        write_to_file=False,
    )
    parser = CodeBlockParser(language="python", evaluator=evaluator)
    sybil = Sybil(parsers=[parser])

    document = sybil.parse(path=rst_file)
    (example,) = list(document)
    example.evaluate()
    outerr = capfd.readouterr()
    assert outerr.out == "Hello, Sybil!\n"
    assert outerr.err == "Hello Stderr!\n"


def test_pass_env(
    rst_file: Path,
    tmp_path: Path,
) -> None:
    """It is possible to pass environment variables to the command."""
    new_file = tmp_path / "new_file.txt"
    evaluator = ShellCommandEvaluator(
        args=[
            "sh",
            "-c",
            f"echo Hello, $ENV_KEY! > {new_file.as_posix()}; exit 0",
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
    env_key = "ENV_KEY"
    os.environ[env_key] = "ENV_VALUE"
    new_file = tmp_path / "new_file.txt"
    evaluator = ShellCommandEvaluator(
        args=[
            "sh",
            "-c",
            f"echo Hello, ${env_key}! > {new_file.as_posix()}; exit 0",
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
    """
    A file with the code block content is passed to the command.

    The file is created with a trailing newline.
    """
    sh_function = """
    cp "$2" "$1"
    """

    file_path = tmp_path / "file.txt"
    evaluator = ShellCommandEvaluator(
        args=["sh", "-c", sh_function, "_", file_path],
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


def test_file_path(rst_file: Path, capfd: pytest.CaptureFixture[str]) -> None:
    """
    The given file path is random and absolute, and starts with a name
    resembling the documentation file name, but without any hyphens
    or periods, except for the period for the final suffix.
    """
    evaluator = ShellCommandEvaluator(
        args=["echo"],
        pad_file=False,
        write_to_file=False,
    )
    parser = CodeBlockParser(language="python", evaluator=evaluator)
    sybil = Sybil(parsers=[parser])

    document = sybil.parse(path=rst_file)
    (example,) = list(document)
    example.evaluate()
    output = capfd.readouterr().out
    given_file_path = Path(output.strip())
    assert given_file_path.parent == rst_file.parent
    assert given_file_path.is_absolute()
    assert not given_file_path.exists()
    assert given_file_path.name.startswith("test_document_example_rst_")
    example.evaluate()
    output = capfd.readouterr().out
    new_given_file_path = Path(output.strip())
    assert new_given_file_path != given_file_path


def test_file_suffix(
    rst_file: Path,
    capfd: pytest.CaptureFixture[str],
) -> None:
    """The given file suffixes are used."""
    suffixes = [".example", ".foobar"]
    evaluator = ShellCommandEvaluator(
        args=["echo"],
        pad_file=False,
        write_to_file=False,
        tempfile_suffixes=suffixes,
    )
    parser = CodeBlockParser(language="python", evaluator=evaluator)
    sybil = Sybil(parsers=[parser])

    document = sybil.parse(path=rst_file)
    (example,) = list(document)
    example.evaluate()
    output = capfd.readouterr().out
    given_file_path = Path(output.strip())
    assert given_file_path.name.startswith("test_document_example_rst_")
    assert given_file_path.suffixes == suffixes


def test_file_prefix(
    rst_file: Path,
    capfd: pytest.CaptureFixture[str],
) -> None:
    """The given file prefixes are used."""
    prefix = "custom_prefix"
    evaluator = ShellCommandEvaluator(
        args=["echo"],
        pad_file=False,
        write_to_file=False,
        tempfile_name_prefix=prefix,
    )
    parser = CodeBlockParser(language="python", evaluator=evaluator)
    sybil = Sybil(parsers=[parser])

    document = sybil.parse(path=rst_file)
    (example,) = list(document)
    example.evaluate()
    output = capfd.readouterr().out
    given_file_path = Path(output.strip())
    assert given_file_path.name.startswith("custom_prefix_")


def test_pad(rst_file: Path, tmp_path: Path) -> None:
    """If pad is True, the file content is padded.

    This test relies heavily on the exact formatting of the
    `rst_file` example.
    """
    sh_function = """
    cp "$2" "$1"
    """

    file_path = tmp_path / "file.txt"
    evaluator = ShellCommandEvaluator(
        args=["sh", "-c", sh_function, "_", file_path],
        pad_file=True,
        write_to_file=False,
    )
    parser = CodeBlockParser(language="python", evaluator=evaluator)
    sybil = Sybil(parsers=[parser])

    document = sybil.parse(path=rst_file)
    (example,) = list(document)
    example.evaluate()
    given_file_content = file_path.read_text(encoding="utf-8")
    expected_content = textwrap.dedent(
        text="""\




        x = 2 + 2
        assert x == 4
        """,
    )
    assert given_file_content == expected_content


@pytest.mark.parametrize(argnames="write_to_file", argvalues=[True, False])
def test_write_to_file(
    tmp_path: Path,
    rst_file: Path,
    *,
    write_to_file: bool,
) -> None:
    """Changes are written to the original file iff `write_to_file` is True."""
    original_content = rst_file.read_text(encoding="utf-8")
    file_with_new_content = tmp_path / "new_file.txt"
    # Add multiple newlines to show that they are not included in the file.
    # No code block ends with multiple newlines.
    new_content = "foobar\n\n"
    file_with_new_content.write_text(data=new_content, encoding="utf-8")
    evaluator = ShellCommandEvaluator(
        args=["cp", file_with_new_content],
        pad_file=False,
        write_to_file=write_to_file,
    )
    parser = CodeBlockParser(language="python", evaluator=evaluator)
    sybil = Sybil(parsers=[parser])

    document = sybil.parse(path=rst_file)
    (example,) = list(document)
    example.evaluate()
    rst_file_content = rst_file.read_text(encoding="utf-8")
    modified_content = textwrap.dedent(
        """\
        Not in code block

        .. code-block:: python

           foobar
        """,
    )
    if write_to_file:
        assert rst_file_content == modified_content
    else:
        assert rst_file_content == original_content


def test_pad_and_write(rst_file: Path) -> None:
    """Changes are written to the original file without the added padding."""
    original_content = rst_file.read_text(encoding="utf-8")
    rst_file.write_text(data=original_content, encoding="utf-8")
    evaluator = ShellCommandEvaluator(
        args=["true"],
        pad_file=True,
        write_to_file=True,
    )
    parser = CodeBlockParser(language="python", evaluator=evaluator)
    sybil = Sybil(parsers=[parser])

    document = sybil.parse(path=rst_file)
    (example,) = list(document)
    example.evaluate()
    rst_file_content = rst_file.read_text(encoding="utf-8")
    assert rst_file_content == original_content


def test_no_changes_mtime(rst_file: Path) -> None:
    """
    The modification time of the file is not changed if no changes are made.
    """
    original_mtime = rst_file.stat().st_mtime
    evaluator = ShellCommandEvaluator(
        args=["true"],
        pad_file=True,
        write_to_file=True,
    )
    parser = CodeBlockParser(language="python", evaluator=evaluator)
    sybil = Sybil(parsers=[parser])

    document = sybil.parse(path=rst_file)
    (example,) = list(document)
    example.evaluate()
    new_mtime = rst_file.stat().st_mtime
    assert new_mtime == original_mtime


def test_non_utf8_output(
    rst_file: Path,
    capfdbinary: pytest.CaptureFixture[bytes],
    tmp_path: Path,
) -> None:
    """Non-UTF-8 output is handled."""
    sh_function = b"""
    echo "\xc0\x80"
    """
    script = tmp_path / "my_script.sh"
    script.write_bytes(data=sh_function)
    script.chmod(mode=stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR)
    evaluator = ShellCommandEvaluator(
        args=["sh", str(script)],
        pad_file=False,
        write_to_file=False,
    )
    parser = CodeBlockParser(language="python", evaluator=evaluator)
    sybil = Sybil(parsers=[parser])

    document = sybil.parse(path=rst_file)
    (example,) = list(document)
    example.evaluate()
    output = capfdbinary.readouterr().out
    assert output == b"\xc0\x80\n"
