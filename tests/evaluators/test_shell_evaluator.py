"""
Tests for the ShellCommandEvaluator.
"""

import os
import platform
import signal
import stat
import subprocess
import sys
import textwrap
import time
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

import charset_normalizer
import click
import pytest
from click.testing import CliRunner
from sybil import Sybil
from sybil.example import Example
from sybil.parsers.markdown.codeblock import (
    CodeBlockParser as MarkdownCodeBlockParser,
)
from sybil.parsers.myst.codeblock import CodeBlockParser as MySTCodeBlockParser
from sybil.parsers.rest.codeblock import CodeBlockParser

from sybil_extras.evaluators.shell_evaluator import ShellCommandEvaluator


@pytest.fixture(
    name="use_pty_option",
    # On CI we cannot use the pseudo-terminal.
    params=[True, False],
)
def fixture_use_pty_option(
    request: pytest.FixtureRequest,
) -> bool:
    """
    Test with and without the pseudo-terminal.
    """
    use_pty = bool(request.param)
    if use_pty and platform.system() == "Windows":  # pragma: no cover
        pytest.skip(reason="PTY is not supported on Windows.")
    return use_pty


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


@dataclass(frozen=True)
class _MarkupLanguageValue:
    """
    Associated values for the supported markup languages.
    """

    name: str
    code_block_parser_cls: type


class _MarkupLanguage(Enum):
    """
    Supported markup languages.
    """

    RESTRUCTUREDTEXT = _MarkupLanguageValue(
        name="reStructuredText",
        code_block_parser_cls=CodeBlockParser,
    )
    MARKDOWN = _MarkupLanguageValue(
        name="Markdown",
        code_block_parser_cls=MarkdownCodeBlockParser,
    )
    MYST = _MarkupLanguageValue(
        name="MyST",
        code_block_parser_cls=MySTCodeBlockParser,
    )


@pytest.fixture(
    name="markup_language",
    params=_MarkupLanguage,
)
def fixture_markup_language(
    request: pytest.FixtureRequest,
) -> _MarkupLanguage:
    """
    Fixture to parametrize over the supported markup languages.
    """
    assert isinstance(request.param, _MarkupLanguage)
    return request.param


def test_error(*, rst_file: Path, use_pty_option: bool) -> None:
    """
    A ``subprocess.CalledProcessError`` is raised if the command fails.
    """
    args = ["sh", "-c", "exit 1"]
    evaluator = ShellCommandEvaluator(
        args=args,
        pad_file=False,
        write_to_file=False,
        use_pty=use_pty_option,
    )
    parser = CodeBlockParser(language="python", evaluator=evaluator)
    sybil = Sybil(parsers=[parser])

    document = sybil.parse(path=rst_file)
    (example,) = document.examples()

    with pytest.raises(
        expected_exception=subprocess.CalledProcessError
    ) as exc:
        example.evaluate()

    assert exc.value.returncode == 1
    # The last element is the path to the temporary file.
    assert exc.value.cmd[:-1] == args


def test_output_shown(
    *,
    rst_file: Path,
    capsys: pytest.CaptureFixture[str],
    use_pty_option: bool,
) -> None:
    """
    Output is shown.
    """
    evaluator = ShellCommandEvaluator(
        args=[
            "sh",
            "-c",
            "echo 'Hello, Sybil!' && echo >&2 'Hello Stderr!'",
        ],
        pad_file=False,
        write_to_file=False,
        use_pty=use_pty_option,
    )
    parser = CodeBlockParser(language="python", evaluator=evaluator)
    sybil = Sybil(parsers=[parser])

    document = sybil.parse(path=rst_file)
    (example,) = document.examples()
    example.evaluate()
    outerr = capsys.readouterr()
    expected_output = "Hello, Sybil!\n"
    expected_stderr = "Hello Stderr!\n"
    if use_pty_option:
        expected_output = "Hello, Sybil!\r\nHello Stderr!\r\n"
        expected_stderr = ""

    assert outerr.out == expected_output
    assert outerr.err == expected_stderr


def test_rm(
    *,
    rst_file: Path,
    capsys: pytest.CaptureFixture[str],
    use_pty_option: bool,
) -> None:
    """
    Output is shown.
    """
    evaluator = ShellCommandEvaluator(
        args=["rm"],
        pad_file=False,
        write_to_file=False,
        use_pty=use_pty_option,
    )
    parser = CodeBlockParser(language="python", evaluator=evaluator)
    sybil = Sybil(parsers=[parser])

    document = sybil.parse(path=rst_file)
    (example,) = document.examples()
    example.evaluate()
    outerr = capsys.readouterr()
    assert outerr.out == ""
    assert outerr.err == ""


def test_pass_env(
    *,
    rst_file: Path,
    tmp_path: Path,
    use_pty_option: bool,
) -> None:
    """
    It is possible to pass environment variables to the command.
    """
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
        use_pty=use_pty_option,
    )
    parser = CodeBlockParser(language="python", evaluator=evaluator)
    sybil = Sybil(parsers=[parser])

    document = sybil.parse(path=rst_file)
    (example,) = document.examples()
    example.evaluate()
    new_file_content = new_file.read_text(encoding="utf-8")
    assert new_file_content == "Hello, ENV_VALUE!\n"


def test_global_env(
    *,
    rst_file: Path,
    tmp_path: Path,
    use_pty_option: bool,
) -> None:
    """
    Global environment variables are sent to the command by default.
    """
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
        use_pty=use_pty_option,
    )
    parser = CodeBlockParser(language="python", evaluator=evaluator)
    sybil = Sybil(parsers=[parser])

    document = sybil.parse(path=rst_file)
    (example,) = document.examples()
    example.evaluate()
    del os.environ[env_key]
    new_file_content = new_file.read_text(encoding="utf-8")
    assert new_file_content == "Hello, ENV_VALUE!\n"


def test_file_is_passed(
    *,
    rst_file: Path,
    tmp_path: Path,
    use_pty_option: bool,
) -> None:
    """A file with the code block content is passed to the command.

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
        use_pty=use_pty_option,
    )
    parser = CodeBlockParser(language="python", evaluator=evaluator)
    sybil = Sybil(parsers=[parser])

    document = sybil.parse(path=rst_file)
    (example,) = document.examples()
    example.evaluate()
    expected_content = "x = 2 + 2\nassert x == 4\n"
    assert file_path.read_text(encoding="utf-8") == expected_content


def test_file_path(
    *,
    rst_file: Path,
    capsys: pytest.CaptureFixture[str],
    use_pty_option: bool,
) -> None:
    """
    The given file path is random and absolute, and starts with a name
    resembling the documentation file name, but without any hyphens or periods,
    except for the period for the final suffix.
    """
    evaluator = ShellCommandEvaluator(
        args=["echo"],
        pad_file=False,
        write_to_file=False,
        use_pty=use_pty_option,
    )
    parser = CodeBlockParser(language="python", evaluator=evaluator)
    sybil = Sybil(parsers=[parser])

    document = sybil.parse(path=rst_file)
    (example,) = document.examples()
    example.evaluate()
    output = capsys.readouterr().out
    stripped_output = output.strip()
    assert stripped_output
    given_file_path = Path(stripped_output)
    assert given_file_path.parent == rst_file.parent
    assert given_file_path.is_absolute()
    assert not given_file_path.exists()
    assert given_file_path.name.startswith("test_document_example_rst_")
    example.evaluate()
    output = capsys.readouterr().out
    new_given_file_path = Path(output.strip())
    assert new_given_file_path != given_file_path


def test_file_suffix(
    *,
    rst_file: Path,
    capsys: pytest.CaptureFixture[str],
    use_pty_option: bool,
) -> None:
    """
    The given file suffixes are used.
    """
    suffixes = [".example", ".foobar"]
    evaluator = ShellCommandEvaluator(
        args=["echo"],
        pad_file=False,
        write_to_file=False,
        tempfile_suffixes=suffixes,
        use_pty=use_pty_option,
    )
    parser = CodeBlockParser(language="python", evaluator=evaluator)
    sybil = Sybil(parsers=[parser])

    document = sybil.parse(path=rst_file)
    (example,) = document.examples()
    example.evaluate()
    output = capsys.readouterr().out
    stripped_output = output.strip()
    assert stripped_output
    given_file_path = Path(stripped_output)
    assert given_file_path.name.startswith("test_document_example_rst_")
    assert given_file_path.suffixes == suffixes


def test_file_prefix(
    *,
    rst_file: Path,
    capsys: pytest.CaptureFixture[str],
    use_pty_option: bool,
) -> None:
    """
    The given file prefixes are used.
    """
    prefix = "custom_prefix"
    evaluator = ShellCommandEvaluator(
        args=["echo"],
        pad_file=False,
        write_to_file=False,
        tempfile_name_prefix=prefix,
        use_pty=use_pty_option,
    )
    parser = CodeBlockParser(language="python", evaluator=evaluator)
    sybil = Sybil(parsers=[parser])

    document = sybil.parse(path=rst_file)
    (example,) = document.examples()
    example.evaluate()
    output = capsys.readouterr().out
    stripped_output = output.strip()
    assert stripped_output
    given_file_path = Path(stripped_output)
    assert given_file_path.name.startswith("custom_prefix_")


def test_pad(*, rst_file: Path, tmp_path: Path, use_pty_option: bool) -> None:
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
        use_pty=use_pty_option,
    )
    parser = CodeBlockParser(language="python", evaluator=evaluator)
    sybil = Sybil(parsers=[parser])

    document = sybil.parse(path=rst_file)
    (example,) = document.examples()
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
def test_write_to_file_new_content_trailing_newlines(
    tmp_path: Path,
    *,
    write_to_file: bool,
    use_pty_option: bool,
    markup_language: _MarkupLanguage,
) -> None:
    """Changes are written to the original file iff `write_to_file` is True.

    If the content has trailing newlines, those are included in code
    block types that allow them.
    """
    original_content = {
        _MarkupLanguage.RESTRUCTUREDTEXT: textwrap.dedent(
            text="""\
            Not in code block

            .. code-block:: python

               x = 2 + 2
               assert x == 4
            """
        ),
        _MarkupLanguage.MARKDOWN: textwrap.dedent(
            text="""\
            Not in code block

            ```python
            x = 2 + 2
            assert x == 4
            ```
            """
        ),
        _MarkupLanguage.MYST: textwrap.dedent(
            text="""\
            Not in code block

            ```{code} python
            x = 2 + 2
            assert x == 4
            ```
            """
        ),
    }[markup_language]
    source_file = tmp_path / "source_file.txt"
    source_file.write_text(data=original_content, encoding="utf-8")
    file_with_new_content = tmp_path / "new_file.txt"
    # Add multiple newlines to show that they are not included in the file.
    # No code block in reSructuredText ends with multiple newlines.
    new_content = "foobar\n\n"
    file_with_new_content.write_text(data=new_content, encoding="utf-8")
    evaluator = ShellCommandEvaluator(
        args=["cp", file_with_new_content],
        pad_file=False,
        write_to_file=write_to_file,
        use_pty=use_pty_option,
    )
    parser = markup_language.value.code_block_parser_cls(
        language="python",
        evaluator=evaluator,
    )
    sybil = Sybil(parsers=[parser])

    document = sybil.parse(path=source_file)
    (example,) = document.examples()
    example.evaluate()
    source_file_content = source_file.read_text(encoding="utf-8")

    expected_content = {
        # There is no code block in reStructuredText that ends with multiple
        # newlines.
        _MarkupLanguage.RESTRUCTUREDTEXT: textwrap.dedent(
            text="""\
            Not in code block

            .. code-block:: python

               foobar
            """
        ),
        _MarkupLanguage.MARKDOWN: textwrap.dedent(
            text="""\
            Not in code block

            ```python
            foobar

            ```
            """
        ),
        _MarkupLanguage.MYST: textwrap.dedent(
            text="""\
            Not in code block

            ```{code} python
            foobar

            ```
            """
        ),
    }[markup_language]
    if write_to_file:
        assert source_file_content == expected_content
    else:
        assert source_file_content == original_content


@pytest.mark.parametrize(argnames="write_to_file", argvalues=[True, False])
def test_write_to_file_new_content_no_trailing_newlines(
    tmp_path: Path,
    *,
    write_to_file: bool,
    use_pty_option: bool,
    markup_language: _MarkupLanguage,
) -> None:
    """Changes are written to the original file iff `write_to_file` is True.

    If the content has no trailing newlines, the new code block is still
    valid.
    """
    original_content = {
        _MarkupLanguage.RESTRUCTUREDTEXT: textwrap.dedent(
            text="""\
            Not in code block

            .. code-block:: python

               x = 2 + 2
               assert x == 4
            """
        ),
        _MarkupLanguage.MARKDOWN: textwrap.dedent(
            text="""\
            Not in code block

            ```python
            x = 2 + 2
            assert x == 4
            ```
            """
        ),
        _MarkupLanguage.MYST: textwrap.dedent(
            text="""\
            Not in code block

            ```{code} python
            x = 2 + 2
            assert x == 4
            ```
            """
        ),
    }[markup_language]
    source_file = tmp_path / "source_file.txt"
    source_file.write_text(data=original_content, encoding="utf-8")
    file_with_new_content = tmp_path / "new_file.txt"
    new_content = "foobar"
    file_with_new_content.write_text(data=new_content, encoding="utf-8")
    evaluator = ShellCommandEvaluator(
        args=["cp", file_with_new_content],
        pad_file=False,
        write_to_file=write_to_file,
        use_pty=use_pty_option,
    )
    parser = markup_language.value.code_block_parser_cls(
        language="python",
        evaluator=evaluator,
    )
    sybil = Sybil(parsers=[parser])

    document = sybil.parse(path=source_file)
    (example,) = document.examples()
    example.evaluate()
    source_file_content = source_file.read_text(encoding="utf-8")

    expected_content = {
        # There is no code block in reStructuredText that ends with multiple
        # newlines.
        _MarkupLanguage.RESTRUCTUREDTEXT: textwrap.dedent(
            text="""\
            Not in code block

            .. code-block:: python

               foobar
            """
        ),
        _MarkupLanguage.MARKDOWN: textwrap.dedent(
            text="""\
            Not in code block

            ```python
            foobar
            ```
            """
        ),
        _MarkupLanguage.MYST: textwrap.dedent(
            text="""\
            Not in code block

            ```{code} python
            foobar
            ```
            """
        ),
    }[markup_language]
    if write_to_file:
        assert source_file_content == expected_content
    else:
        assert source_file_content == original_content


def test_write_to_file_indented_existing_block(
    tmp_path: Path,
    *,
    use_pty_option: bool,
    markup_language: _MarkupLanguage,
) -> None:
    """
    Changes are written to indented code blocks.
    """
    original_content = {
        _MarkupLanguage.RESTRUCTUREDTEXT: textwrap.dedent(
            text="""\
            Not in code block

                .. code-block:: python

                   x = 2 + 2
                   assert x == 4
            """
        ),
        _MarkupLanguage.MARKDOWN: textwrap.dedent(
            text="""\
            Not in code block

                ```python
                x = 2 + 2
                assert x == 4
                ```
            """
        ),
        _MarkupLanguage.MYST: textwrap.dedent(
            text="""\
            Not in code block

                ```{code} python
                x = 2 + 2
                assert x == 4
                ```
            """
        ),
    }[markup_language]
    source_file = tmp_path / "source_file.txt"
    source_file.write_text(data=original_content, encoding="utf-8")
    file_with_new_content = tmp_path / "new_file.txt"
    new_content = "foobar"
    file_with_new_content.write_text(data=new_content, encoding="utf-8")
    evaluator = ShellCommandEvaluator(
        args=["cp", file_with_new_content],
        pad_file=False,
        write_to_file=True,
        use_pty=use_pty_option,
    )
    parser = markup_language.value.code_block_parser_cls(
        language="python",
        evaluator=evaluator,
    )
    sybil = Sybil(parsers=[parser])

    document = sybil.parse(path=source_file)
    (example,) = document.examples()
    example.evaluate()
    source_file_content = source_file.read_text(encoding="utf-8")

    expected_content = {
        # There is no code block in reStructuredText that ends with multiple
        # newlines.
        _MarkupLanguage.RESTRUCTUREDTEXT: textwrap.dedent(
            text="""\
            Not in code block

                .. code-block:: python

                   foobar
            """
        ),
        _MarkupLanguage.MARKDOWN: textwrap.dedent(
            text="""\
            Not in code block

                ```python
                foobar
                ```
            """
        ),
        _MarkupLanguage.MYST: textwrap.dedent(
            text="""\
            Not in code block

                ```{code} python
                foobar
                ```
            """
        ),
    }[markup_language]
    assert source_file_content == expected_content


def test_write_to_file_indented_empty_existing_block(
    tmp_path: Path,
    *,
    use_pty_option: bool,
    markup_language: _MarkupLanguage,
) -> None:
    """
    Changes are written to indented code blocks.
    """
    original_content = {
        _MarkupLanguage.RESTRUCTUREDTEXT: textwrap.dedent(
            text="""\
            Not in code block

                    .. code-block:: python

            After code block
            """
        ),
        _MarkupLanguage.MARKDOWN: textwrap.dedent(
            text="""\
            Not in code block

                    ```python
                    ```

            After code block
            """
        ),
        _MarkupLanguage.MYST: textwrap.dedent(
            text="""\
            Not in code block

                    ```{code} python
                    ```

            After code block
            """
        ),
    }[markup_language]
    source_file = tmp_path / "source_file.txt"
    source_file.write_text(data=original_content, encoding="utf-8")
    file_with_new_content = tmp_path / "new_file.txt"
    new_content = "foobar"
    file_with_new_content.write_text(data=new_content, encoding="utf-8")
    evaluator = ShellCommandEvaluator(
        args=["cp", file_with_new_content],
        pad_file=False,
        write_to_file=True,
        use_pty=use_pty_option,
    )
    parser = markup_language.value.code_block_parser_cls(
        language="python",
        evaluator=evaluator,
    )
    sybil = Sybil(parsers=[parser])

    document = sybil.parse(path=source_file)
    (example,) = document.examples()
    example.evaluate()
    source_file_content = source_file.read_text(encoding="utf-8")

    expected_content = {
        # There is no code block in reStructuredText that ends with multiple
        # newlines.
        _MarkupLanguage.RESTRUCTUREDTEXT: textwrap.dedent(
            text="""\
            Not in code block

                    .. code-block:: python

                       foobar

            After code block
            """
        ),
        _MarkupLanguage.MARKDOWN: textwrap.dedent(
            text="""\
            Not in code block

                    ```python
                    foobar
                    ```

            After code block
            """
        ),
        _MarkupLanguage.MYST: textwrap.dedent(
            text="""\
            Not in code block

                    ```{code} python
                    foobar
                    ```

            After code block
            """
        ),
    }[markup_language]
    assert source_file_content == expected_content


def test_write_to_file_multiple(*, tmp_path: Path) -> None:
    """
    If multiple code blocks are present with the same content, changes are
    written to the code block which needs changing.
    """
    content = textwrap.dedent(
        text="""\
        Not in code block

        .. code-block:: python

           x = 2 + 2
           assert x == 4

        .. code-block:: python

           x = 2 + 2
           assert x == 4

        .. code-block:: python

           x = 2 + 2
           assert x == 4
        """
    )
    rst_file = tmp_path / "test_document.example.rst"
    rst_file.write_text(data=content, encoding="utf-8")
    file_with_new_content = tmp_path / "new_file.txt"
    # Add multiple newlines to show that they are not included in the file.
    # No code block in reSructuredText ends with multiple newlines.
    new_content = "foobar\n\n"
    file_with_new_content.write_text(data=new_content, encoding="utf-8")
    evaluator = ShellCommandEvaluator(
        args=["cp", file_with_new_content],
        pad_file=False,
        write_to_file=True,
        use_pty=False,
    )
    parser = CodeBlockParser(language="python", evaluator=evaluator)
    sybil = Sybil(parsers=[parser])

    document = sybil.parse(path=rst_file)
    (_, second_example, third_example) = document.examples()
    second_example.evaluate()
    rst_file_content = rst_file.read_text(encoding="utf-8")
    expected_content = textwrap.dedent(
        text="""\
        Not in code block

        .. code-block:: python

           x = 2 + 2
           assert x == 4

        .. code-block:: python

           foobar

        .. code-block:: python

           x = 2 + 2
           assert x == 4
        """,
    )
    assert rst_file_content == expected_content

    third_example.evaluate()
    expected_content = textwrap.dedent(
        text="""\
        Not in code block

        .. code-block:: python

           x = 2 + 2
           assert x == 4

        .. code-block:: python

           foobar

        .. code-block:: python

           foobar
        """,
    )

    rst_file_content = rst_file.read_text(encoding="utf-8")
    assert rst_file_content == expected_content


def test_pad_and_write(*, rst_file: Path, use_pty_option: bool) -> None:
    """
    Changes are written to the original file without the added padding.
    """
    original_content = rst_file.read_text(encoding="utf-8")
    rst_file.write_text(data=original_content, encoding="utf-8")
    evaluator = ShellCommandEvaluator(
        args=["true"],
        pad_file=True,
        write_to_file=True,
        use_pty=use_pty_option,
    )
    parser = CodeBlockParser(language="python", evaluator=evaluator)
    sybil = Sybil(parsers=[parser])

    document = sybil.parse(path=rst_file)
    (example,) = document.examples()
    example.evaluate()
    rst_file_content = rst_file.read_text(encoding="utf-8")
    assert rst_file_content == original_content


def test_no_changes_mtime(*, rst_file: Path, use_pty_option: bool) -> None:
    """
    The modification time of the file is not changed if no changes are made.
    """
    original_mtime = rst_file.stat().st_mtime
    evaluator = ShellCommandEvaluator(
        args=["true"],
        pad_file=True,
        write_to_file=True,
        use_pty=use_pty_option,
    )
    parser = CodeBlockParser(language="python", evaluator=evaluator)
    sybil = Sybil(parsers=[parser])

    document = sybil.parse(path=rst_file)
    (example,) = document.examples()
    example.evaluate()
    new_mtime = rst_file.stat().st_mtime
    assert new_mtime == original_mtime


def test_non_utf8_output(
    *,
    rst_file: Path,
    capsysbinary: pytest.CaptureFixture[bytes],
    tmp_path: Path,
    use_pty_option: bool,
) -> None:
    """
    Non-UTF-8 output is handled.
    """
    sh_function = b"""
    echo "\xc0\x80"
    """
    script = tmp_path / "my_script.sh"
    script.write_bytes(data=sh_function)
    script.chmod(mode=stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR)
    evaluator = ShellCommandEvaluator(
        args=["sh", str(object=script)],
        pad_file=False,
        write_to_file=False,
        use_pty=use_pty_option,
    )
    parser = CodeBlockParser(language="python", evaluator=evaluator)
    sybil = Sybil(parsers=[parser])

    document = sybil.parse(path=rst_file)
    (example,) = document.examples()
    example.evaluate()
    output = capsysbinary.readouterr().out
    expected_output = b"\xc0\x80\n"
    if use_pty_option:
        expected_output = expected_output.replace(b"\n", b"\r\n")
    assert output == expected_output


def test_no_file_left_behind_on_interruption(
    rst_file: Path,
    tmp_path: Path,
) -> None:
    """
    No file is left behind if the process is interrupted.
    """
    sleep_python_script_content = textwrap.dedent(
        text="""\
        import time

        time.sleep(0.5)
        """,
    )

    sleep_python_script = tmp_path / "sleep_comand.py"
    sleep_python_script.write_text(
        data=sleep_python_script_content,
        encoding="utf-8",
    )

    run_shell_command_evaluator_script_content = textwrap.dedent(
        text=f"""\
        import sys
        from pathlib import PosixPath, Path

        from sybil import Sybil
        from sybil.parsers.rest.codeblock import CodeBlockParser

        from sybil_extras.evaluators.shell_evaluator import (
            ShellCommandEvaluator,
        )

        evaluator = ShellCommandEvaluator(
            args=[sys.executable, "{sleep_python_script.as_posix()}"],
            pad_file=False,
            write_to_file=True,
            use_pty=False,
        )

        parser = CodeBlockParser(language="python", evaluator=evaluator)
        sybil = Sybil(parsers=[parser])

        document = sybil.parse(path=Path("{rst_file.as_posix()}"))
        (example,) = document.examples()
        example.evaluate()
        """,
    )

    evaluator_script = tmp_path / "evaluator_script.py"
    evaluator_script.write_text(
        data=run_shell_command_evaluator_script_content,
        encoding="utf-8",
    )

    # Sanity check the script by checking that it can run fine.
    run_script_args = [sys.executable, str(object=evaluator_script)]
    subprocess.run(args=run_script_args, check=True)

    with subprocess.Popen(args=run_script_args) as evaluator_process:
        time.sleep(0.1)
        os.kill(evaluator_process.pid, signal.SIGINT)
        evaluator_process.wait()

    assert set(rst_file.parent.glob(pattern="**/*")) == {
        rst_file,
        evaluator_script,
        sleep_python_script,
    }


@pytest.mark.parametrize(argnames="source_newline", argvalues=["\n", "\r\n"])
def test_newline_system(
    *,
    rst_file: Path,
    tmp_path: Path,
    source_newline: str,
    use_pty_option: bool,
) -> None:
    """
    The system line endings are used by default.
    """
    rst_file_contents = rst_file.read_text(encoding="utf-8")
    rst_file.write_text(data=rst_file_contents, newline=source_newline)
    sh_function = """
    cp "$2" "$1"
    """

    file_path = tmp_path / "file.txt"
    evaluator = ShellCommandEvaluator(
        args=["sh", "-c", sh_function, "_", file_path],
        pad_file=False,
        write_to_file=False,
        use_pty=use_pty_option,
    )
    parser = CodeBlockParser(language="python", evaluator=evaluator)
    sybil = Sybil(parsers=[parser])

    document = sybil.parse(path=rst_file)
    (example,) = document.examples()
    example.evaluate()
    content_bytes = file_path.read_bytes()
    includes_crlf = b"\r\n" in content_bytes
    default_is_crlf = os.linesep == "\r\n"
    assert includes_crlf == default_is_crlf


@pytest.mark.parametrize(argnames="source_newline", argvalues=["\n", "\r\n"])
@pytest.mark.parametrize(
    argnames=("given_newline", "expect_crlf"),
    argvalues=[
        ("\n", False),
        ("\r\n", True),
    ],
)
def test_newline_given(
    *,
    rst_file: Path,
    tmp_path: Path,
    source_newline: str,
    given_newline: str,
    expect_crlf: bool,
    use_pty_option: bool,
) -> None:
    """
    The given line ending option is used.
    """
    rst_file_contents = rst_file.read_text(encoding="utf-8")
    rst_file.write_text(data=rst_file_contents, newline=source_newline)
    sh_function = """
    cp "$2" "$1"
    """

    file_path = tmp_path / "file.txt"
    evaluator = ShellCommandEvaluator(
        args=["sh", "-c", sh_function, "_", file_path],
        pad_file=False,
        write_to_file=False,
        newline=given_newline,
        use_pty=use_pty_option,
    )
    parser = CodeBlockParser(language="python", evaluator=evaluator)
    sybil = Sybil(parsers=[parser])

    document = sybil.parse(path=rst_file)
    (example,) = document.examples()
    example.evaluate()
    content_bytes = file_path.read_bytes()
    includes_crlf = b"\r\n" in content_bytes
    includes_lf = b"\n" in content_bytes
    assert includes_crlf == expect_crlf
    assert includes_lf


@pytest.mark.parametrize(
    argnames="write_to_file_option",
    argvalues=[True, False],
)
def test_empty_code_block_write_content_to_file(
    *,
    tmp_path: Path,
    use_pty_option: bool,
    write_to_file_option: bool,
    markup_language: _MarkupLanguage,
) -> None:
    """
    An error is given when trying to write content to an empty code block.
    """
    rst_content = textwrap.dedent(
        text="""\
        Not in code block

        .. code-block:: python

        After empty code block
        """,
    )
    markdown_content = textwrap.dedent(
        text="""\
        Not in code block

        ```python
        ```

        After empty code block
        """,
    )

    myst_content = textwrap.dedent(
        text="""\
        Not in code block

        ```{code} python
        ```

        After empty code block
        """,
    )

    content = {
        _MarkupLanguage.RESTRUCTUREDTEXT: rst_content,
        _MarkupLanguage.MARKDOWN: markdown_content,
        _MarkupLanguage.MYST: myst_content,
    }[markup_language]
    source_file = tmp_path / "source_file.txt"
    source_file.write_text(data=content, encoding="utf-8")
    file_with_new_content = tmp_path / "new_file.txt"
    # Add multiple newlines to show that they are not included in the file.
    # No code block in reSructuredText ends with multiple newlines.
    new_content = "foobar\n\n"
    file_with_new_content.write_text(data=new_content, encoding="utf-8")
    evaluator = ShellCommandEvaluator(
        args=["cp", file_with_new_content],
        pad_file=False,
        write_to_file=write_to_file_option,
        use_pty=use_pty_option,
    )

    parser = markup_language.value.code_block_parser_cls(
        language="python",
        evaluator=evaluator,
    )
    sybil = Sybil(parsers=[parser])

    document = sybil.parse(path=source_file)
    (example,) = document.examples()

    expected_modified_content = {
        # There is no code block in reStructuredText that ends with multiple
        # newlines.
        _MarkupLanguage.RESTRUCTUREDTEXT: textwrap.dedent(
            text="""\
            Not in code block

            .. code-block:: python

               foobar

            After empty code block
            """
        ),
        _MarkupLanguage.MARKDOWN: textwrap.dedent(
            text="""\
            Not in code block

            ```python
            foobar

            ```

            After empty code block
            """
        ),
        _MarkupLanguage.MYST: textwrap.dedent(
            text="""\
            Not in code block

            ```{code} python
            foobar

            ```

            After empty code block
            """
        ),
    }[markup_language]

    example.evaluate()
    new_content = source_file.read_text(encoding="utf-8")

    if write_to_file_option:
        assert new_content == expected_modified_content
    else:
        assert new_content == content


def test_empty_code_block_write_content_to_file_with_options(
    *,
    tmp_path: Path,
    use_pty_option: bool,
    markup_language: _MarkupLanguage,
) -> None:
    """
    It is possible to write content to an empty code block even if that code
    block has options.
    """
    if markup_language == _MarkupLanguage.MARKDOWN:
        # Markdown does not support code block options.
        return

    rst_content = textwrap.dedent(
        text="""\
        Not in code block

        .. code-block:: python
           :emphasize-lines: 2,3

        After empty code block
        """,
    )

    myst_content = textwrap.dedent(
        text="""\
        Not in code block

        ```{code} python
        :emphasize-lines: 2,3
        ```

        After empty code block
        """,
    )

    content = {
        _MarkupLanguage.RESTRUCTUREDTEXT: rst_content,
        _MarkupLanguage.MYST: myst_content,
    }[markup_language]
    source_file = tmp_path / "source_file.txt"
    source_file.write_text(data=content, encoding="utf-8")
    file_with_new_content = tmp_path / "new_file.txt"
    new_content = "foobar"
    file_with_new_content.write_text(data=new_content, encoding="utf-8")
    evaluator = ShellCommandEvaluator(
        args=["cp", file_with_new_content],
        pad_file=False,
        write_to_file=True,
        use_pty=use_pty_option,
    )

    parser = markup_language.value.code_block_parser_cls(
        language="python",
        evaluator=evaluator,
    )
    sybil = Sybil(parsers=[parser])

    document = sybil.parse(path=source_file)
    (example,) = document.examples()

    expected_modified_content = {
        # There is no code block in reStructuredText that ends with multiple
        # newlines.
        _MarkupLanguage.RESTRUCTUREDTEXT: textwrap.dedent(
            text="""\
            Not in code block

            .. code-block:: python
               :emphasize-lines: 2,3

               foobar

            After empty code block
            """
        ),
        _MarkupLanguage.MYST: textwrap.dedent(
            text="""\
            Not in code block

            ```{code} python
            :emphasize-lines: 2,3
            foobar
            ```

            After empty code block
            """
        ),
    }[markup_language]

    example.evaluate()
    new_content = source_file.read_text(encoding="utf-8")

    assert new_content == expected_modified_content


@pytest.mark.parametrize(
    argnames="new_content",
    argvalues=[
        "",
        # Code blocks in reStructuredText cannot contain just newlines.
        # Therefore we treat this as an empty code block.
        "\n\n",
    ],
)
def test_empty_code_block_write_empty_to_file(
    *,
    tmp_path: Path,
    rst_file: Path,
    use_pty_option: bool,
    new_content: str,
) -> None:
    """
    No error is given when trying to write empty content to an empty code
    block.
    """
    content = textwrap.dedent(
        text="""\
        Not in code block

        .. code-block:: python

        After empty code block
        """
    )
    rst_file.write_text(data=content, encoding="utf-8")
    file_with_new_content = tmp_path / "new_file.txt"
    file_with_new_content.write_text(data=new_content, encoding="utf-8")
    evaluator = ShellCommandEvaluator(
        args=["cp", file_with_new_content],
        pad_file=False,
        write_to_file=True,
        use_pty=use_pty_option,
    )
    parser = CodeBlockParser(language="python", evaluator=evaluator)
    sybil = Sybil(parsers=[parser])

    document = sybil.parse(path=rst_file)
    (example,) = document.examples()
    example.evaluate()
    assert rst_file.read_text(encoding="utf-8") == content


def test_bad_command_error(*, rst_file: Path, use_pty_option: bool) -> None:
    """
    A ``subprocess.CalledProcessError`` is raised if the command is invalid.
    """
    args = ["sh", "--unknownoption"]
    evaluator = ShellCommandEvaluator(
        args=args,
        pad_file=False,
        write_to_file=False,
        use_pty=use_pty_option,
    )
    parser = CodeBlockParser(language="python", evaluator=evaluator)
    sybil = Sybil(parsers=[parser])

    document = sybil.parse(path=rst_file)
    (example,) = document.examples()

    with pytest.raises(
        expected_exception=subprocess.CalledProcessError
    ) as exc:
        example.evaluate()

    expected_returncode = 2
    assert exc.value.returncode == expected_returncode
    # The last element is the path to the temporary file.
    assert exc.value.cmd[:-1] == args


def test_click_runner(*, rst_file: Path, use_pty_option: bool) -> None:
    """
    The click runner can pick up the command output.
    """

    @click.command()
    def _main() -> None:
        """
        Click command to run a shell command.
        """
        evaluator = ShellCommandEvaluator(
            args=[
                "sh",
                "-c",
                "echo 'Hello, Sybil!' && echo >&2 'Hello Stderr!'",
            ],
            pad_file=False,
            write_to_file=False,
            use_pty=use_pty_option,
        )
        parser = CodeBlockParser(language="python", evaluator=evaluator)
        sybil = Sybil(parsers=[parser])

        document = sybil.parse(path=rst_file)
        (example,) = document.examples()
        example.evaluate()

    runner = CliRunner(mix_stderr=False)
    result = runner.invoke(cli=_main)
    assert result.exit_code == 0, (result.stdout, result.stderr)
    expected_output = "Hello, Sybil!\n"
    expected_stderr = "Hello Stderr!\n"
    if use_pty_option:
        expected_output = "Hello, Sybil!\nHello Stderr!\n"
        expected_stderr = ""

    assert result.stdout == expected_output
    assert result.stderr == expected_stderr


@pytest.mark.parametrize(
    argnames="encoding",
    argvalues=["utf_8", "utf_16"],
)
def test_encoding(
    *,
    tmp_path: Path,
    rst_file: Path,
    use_pty_option: bool,
    encoding: str,
) -> None:
    """
    The given encoding is used.
    """
    sh_function = """
    cp "$2" "$1"
    """

    file_path = tmp_path / "file.txt"
    content = textwrap.dedent(
        text="""\
        Not in code block

        .. code-block:: python

           😀
        """
    )
    rst_file.write_text(data=content, encoding=encoding)
    evaluator = ShellCommandEvaluator(
        args=["sh", "-c", sh_function, "_", file_path],
        pad_file=False,
        write_to_file=True,
        use_pty=use_pty_option,
        encoding=encoding,
    )

    parser = CodeBlockParser(language="python", evaluator=evaluator)
    sybil = Sybil(parsers=[parser], encoding=encoding)

    document = sybil.parse(path=rst_file)
    (example,) = document.examples()
    example.evaluate()

    normalizer_guesses = charset_normalizer.from_bytes(
        sequences=file_path.read_bytes(),
    )
    best_guess = normalizer_guesses.best()
    assert best_guess is not None
    assert best_guess.encoding == encoding


def test_custom_on_modify_no_modification(
    *,
    rst_file: Path,
    use_pty_option: bool,
) -> None:
    """
    The custom `on_modify` function is not called when there is a modification.
    """

    def on_modify(example: Example, modified_example_content: str) -> None:
        """
        Raise an error if this function is called.
        """
        del example
        del modified_example_content
        msg = "This should not be called."
        raise ValueError(msg)

    evaluator = ShellCommandEvaluator(
        args=["true"],
        pad_file=True,
        write_to_file=True,
        use_pty=use_pty_option,
        on_modify=on_modify,
    )

    parser = CodeBlockParser(language="python", evaluator=evaluator)
    sybil = Sybil(parsers=[parser])
    document = sybil.parse(path=rst_file)
    (example,) = document.examples()
    # This does not raise an error, so the custom `on_modify` function is not
    # called.
    example.evaluate()

    # Call the function directly to ensure it raises an error, and for
    # coverage.
    with pytest.raises(
        expected_exception=ValueError,
        match="This should not be called.",
    ):
        on_modify(example=example, modified_example_content="")


def test_custom_on_modify_with_modification(
    *,
    rst_file: Path,
    use_pty_option: bool,
    tmp_path: Path,
) -> None:
    """
    The custom `on_modify` function is called when there is a modification.
    """

    def on_modify(example: Example, modified_example_content: str) -> None:
        """
        Check that the given content is as expected.
        """
        assert modified_example_content == "foobar"
        assert example.path == str(object=rst_file)

    file_with_new_content = tmp_path / "new_file.txt"
    new_content = "foobar"
    file_with_new_content.write_text(data=new_content, encoding="utf-8")
    evaluator = ShellCommandEvaluator(
        args=["cp", file_with_new_content],
        pad_file=False,
        write_to_file=True,
        use_pty=use_pty_option,
        on_modify=on_modify,
    )

    parser = CodeBlockParser(language="python", evaluator=evaluator)
    sybil = Sybil(parsers=[parser])
    document = sybil.parse(path=rst_file)
    (example,) = document.examples()
    example.evaluate()
