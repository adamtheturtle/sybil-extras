"""Tests for PyconsShellCommandEvaluator."""

import subprocess
import textwrap
import uuid
from pathlib import Path

import pytest
from beartype import beartype
from sybil import Sybil
from sybil.example import Example
from sybil.parsers.markdown import (
    CodeBlockParser as SybilMarkdownCodeBlockParser,
)

from sybil_extras.evaluators.pycon_shell_evaluator import (
    PyconsShellCommandEvaluator,
    pycon_to_python,
    python_to_pycon,
)


@beartype
def make_temp_file_path(*, example: Example) -> Path:
    """Create a temporary file path for an example code block."""
    return Path(example.path).parent / f"temp_{uuid.uuid4().hex[:8]}.py"


class TestPyconToPython:
    """Tests for pycon_to_python."""

    def test_simple_statements(self) -> None:
        """Simple >>> lines become plain Python lines."""
        pycon = textwrap.dedent(
            text="""\
            >>> x = 1
            >>> y = 2
            """,
        )
        assert pycon_to_python(pycon_text=pycon) == textwrap.dedent(
            text="""\
            x = 1
            y = 2
            """,
        )

    def test_output_lines_dropped(self) -> None:
        """Output lines (no prompt) are discarded."""
        pycon = textwrap.dedent(
            text="""\
            >>> x = 1 + 1
            >>> x
            2
            """,
        )
        assert pycon_to_python(pycon_text=pycon) == textwrap.dedent(
            text="""\
            x = 1 + 1
            x
            """,
        )

    def test_continuation_lines(self) -> None:
        """... continuation lines have their prefix stripped."""
        pycon = textwrap.dedent(
            text="""\
            >>> def foo():
            ...     return 1
            """,
        )
        expected = textwrap.dedent(
            text="""\
            def foo():
                return 1
            """,
        )
        assert pycon_to_python(pycon_text=pycon) == expected

    def test_empty_prompt_lines(self) -> None:
        """Bare >>> and ... (no trailing space) become empty lines."""
        pycon = ">>>\n...\n"
        assert pycon_to_python(pycon_text=pycon) == "\n\n"

    def test_empty_string(self) -> None:
        """Empty input returns empty string."""
        assert pycon_to_python(pycon_text="") == ""


class TestPythonToPycon:
    """Tests for python_to_pycon."""

    def test_simple_statement(self) -> None:
        """A simple assignment gets >>> prefix."""
        result = python_to_pycon(
            python_text="x = 1\n",
            original_pycon=">>> x = 1\n",
        )
        assert result == ">>> x = 1\n"

    def test_output_lines_preserved(self) -> None:
        """Output lines from the original are preserved."""
        result = python_to_pycon(
            python_text="x\n",
            original_pycon=textwrap.dedent(
                text="""\
                >>> x
                42
                """,
            ),
        )
        assert result == textwrap.dedent(
            text="""\
            >>> x
            42
            """,
        )

    def test_multiline_statement(self) -> None:
        """Multi-line statements get >>> on first line, ... on rest."""
        python = textwrap.dedent(
            text="""\
            def foo():
                return 1
            """,
        )
        original = textwrap.dedent(
            text="""\
            >>> def foo():
            ...     return 1
            """,
        )
        result = python_to_pycon(
            python_text=python,
            original_pycon=original,
        )
        assert result == textwrap.dedent(
            text="""\
            >>> def foo():
            ...     return 1
            """,
        )

    def test_statement_count_mismatch_drops_output(self) -> None:
        """When statement count differs from chunk count, output is not
        added.
        """
        # original has 1 chunk but formatted python has 2 statements
        result = python_to_pycon(
            python_text=textwrap.dedent(
                text="""\
                x = 1
                y = 2
                """,
            ),
            original_pycon=textwrap.dedent(
                text="""\
                >>> x = 1 + y = 2
                output
                """,
            ),
        )
        # Output not preserved since chunk count != statement count
        assert "output" not in result

    def test_multiple_statements_with_output(self) -> None:
        """Multiple statements each get their output lines appended."""
        original = textwrap.dedent(
            text="""\
            >>> x = 1
            >>> x
            1
            >>> y = 2
            >>> y
            2
            """,
        )
        python = textwrap.dedent(
            text="""\
            x = 1
            x
            y = 2
            y
            """,
        )
        result = python_to_pycon(
            python_text=python,
            original_pycon=original,
        )
        assert result == textwrap.dedent(
            text="""\
            >>> x = 1
            >>> x
            1
            >>> y = 2
            >>> y
            2
            """,
        )

    def test_syntax_error_fallback(self) -> None:
        """Invalid Python falls back to prefixing each line with >>>."""
        result = python_to_pycon(
            python_text="def (\n",
            original_pycon=">>> def (\n",
        )
        assert result == ">>> def (\n"


class TestPyconsShellCommandEvaluator:
    """Tests for PyconsShellCommandEvaluator."""

    @pytest.fixture(name="md_pycon_file")
    def fixture_md_pycon_file(self, tmp_path: Path) -> Path:
        """Create a Markdown file with a pycon code block."""
        content = textwrap.dedent(
            text="""\
            Some text.

            ```pycon
            >>> x = 1 + 1
            >>> x
            2
            ```
            """
        )
        test_file = tmp_path / "test_doc.md"
        test_file.write_text(data=content, encoding="utf-8")
        return test_file

    def test_error_on_nonzero_exit(self, *, tmp_path: Path) -> None:
        """A CalledProcessError is raised when the command fails."""
        content = textwrap.dedent(
            text="""\
            ```pycon
            >>> x = 1
            ```
            """,
        )
        test_file = tmp_path / "test.md"
        test_file.write_text(data=content, encoding="utf-8")

        evaluator = PyconsShellCommandEvaluator(
            args=["sh", "-c", "exit 1"],
            temp_file_path_maker=make_temp_file_path,
            pad_file=False,
            write_to_file=False,
            use_pty=False,
        )
        parser = SybilMarkdownCodeBlockParser(
            language="pycon",
            evaluator=evaluator,
        )
        sybil = Sybil(parsers=[parser])
        document = sybil.parse(path=test_file)
        (example,) = document.examples()

        with pytest.raises(expected_exception=subprocess.CalledProcessError):
            example.evaluate()

    def test_writes_extracted_python_to_temp_file(
        self,
        *,
        tmp_path: Path,
    ) -> None:
        """Only Python input lines (without >>> prompts) reach the command."""
        script = tmp_path / "capture.sh"
        captured = tmp_path / "captured.txt"
        script.write_text(
            data=f'cat "$1" > {captured.as_posix()}',
            encoding="utf-8",
        )
        script.chmod(mode=0o755)

        content = textwrap.dedent(
            text="""\
            ```pycon
            >>> x = 1 + 1
            >>> x
            2
            ```
            """,
        )
        test_file = tmp_path / "test.md"
        test_file.write_text(data=content, encoding="utf-8")

        evaluator = PyconsShellCommandEvaluator(
            args=["sh", script.as_posix()],
            temp_file_path_maker=make_temp_file_path,
            pad_file=False,
            write_to_file=False,
            use_pty=False,
        )
        parser = SybilMarkdownCodeBlockParser(
            language="pycon",
            evaluator=evaluator,
        )
        sybil = Sybil(parsers=[parser])
        document = sybil.parse(path=test_file)
        (example,) = document.examples()
        example.evaluate()

        written = captured.read_text(encoding="utf-8")
        # The temp file should contain Python, not pycon
        assert ">>>" not in written
        assert "x = 1 + 1\n" in written
        assert "x\n" in written

    def test_write_to_file_reformats_pycon(
        self,
        *,
        tmp_path: Path,
    ) -> None:
        """Write_to_file=True rewrites the block in pycon format."""
        content = textwrap.dedent(
            text="""\
            ```pycon
            >>> x=1+1
            >>> x
            2
            ```
            """
        )
        test_file = tmp_path / "test.md"
        test_file.write_text(data=content, encoding="utf-8")

        # Use a script that adds spaces around the = sign
        script = tmp_path / "fmt.py"
        script.write_text(
            data=textwrap.dedent(
                text="""\
                import sys, re, pathlib
                path = pathlib.Path(sys.argv[1])
                text = path.read_text()
                text = text.replace("x=1+1", "x = 1 + 1")
                path.write_text(text)
                """
            ),
            encoding="utf-8",
        )

        evaluator = PyconsShellCommandEvaluator(
            args=["python3", str(object=script)],
            temp_file_path_maker=make_temp_file_path,
            pad_file=False,
            write_to_file=True,
            use_pty=False,
        )
        parser = SybilMarkdownCodeBlockParser(
            language="pycon",
            evaluator=evaluator,
        )
        sybil = Sybil(parsers=[parser])
        document = sybil.parse(path=test_file)
        (example,) = document.examples()
        example.evaluate()

        result = test_file.read_text(encoding="utf-8")
        # The file should now have formatted pycon content
        assert ">>> x = 1 + 1\n" in result
        # Output line should be preserved
        assert "2\n" in result

    def test_no_change_leaves_file_unmodified(
        self,
        *,
        tmp_path: Path,
    ) -> None:
        """When the command makes no changes the file is left
        untouched.
        """
        content = textwrap.dedent(
            text="""\
            ```pycon
            >>> x = 1
            ```
            """,
        )
        test_file = tmp_path / "test.md"
        test_file.write_text(data=content, encoding="utf-8")
        mtime_before = test_file.stat().st_mtime

        evaluator = PyconsShellCommandEvaluator(
            args=["true"],
            temp_file_path_maker=make_temp_file_path,
            pad_file=False,
            write_to_file=True,
            use_pty=False,
        )
        parser = SybilMarkdownCodeBlockParser(
            language="pycon",
            evaluator=evaluator,
        )
        sybil = Sybil(parsers=[parser])
        document = sybil.parse(path=test_file)
        (example,) = document.examples()
        example.evaluate()

        assert test_file.stat().st_mtime == mtime_before
