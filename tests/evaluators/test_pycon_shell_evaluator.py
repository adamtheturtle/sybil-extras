"""Tests for pycon source preparer and result transformer."""

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

from sybil_extras.evaluators.shell_evaluator import ShellCommandEvaluator
from sybil_extras.evaluators.shell_evaluator.exceptions import (
    InvalidPyconError,
)
from sybil_extras.evaluators.shell_evaluator.result_transformer import (
    PyconResultTransformer,
)
from sybil_extras.evaluators.shell_evaluator.source_preparer import (
    PyconSourcePreparer,
)


@beartype
def make_temp_file_path(*, example: Example) -> Path:
    """Create a temporary file path for an example code block."""
    return Path(example.path).parent / f"temp_{uuid.uuid4().hex[:8]}.py"


@beartype
def _make_pycon_evaluator(
    *,
    args: list[str | Path],
    pad_file: bool = False,
    write_to_file: bool = False,
    use_pty: bool = False,
) -> ShellCommandEvaluator:
    """Create an evaluator for pycon code blocks."""
    return ShellCommandEvaluator(
        args=args,
        temp_file_path_maker=make_temp_file_path,
        pad_file=pad_file,
        write_to_file=write_to_file,
        use_pty=use_pty,
        source_preparer=PyconSourcePreparer(),
        result_transformer=PyconResultTransformer(),
    )


def test_writes_extracted_python_to_temp_file(
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

    evaluator = _make_pycon_evaluator(
        args=["sh", script.as_posix()],
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
    expected = textwrap.dedent(
        text="""\
        x = 1 + 1
        x
        """,
    )
    assert written == expected


def test_write_to_file_reformats_pycon(
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

    evaluator = _make_pycon_evaluator(
        args=["python3", str(object=script)],
        write_to_file=True,
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
    assert result == textwrap.dedent(
        text="""\
        ```pycon
        >>> x = 1 + 1
        >>> x
        2
        ```
        """,
    )


def test_no_change_leaves_file_unmodified(
    *,
    tmp_path: Path,
) -> None:
    """When the command makes no changes the file is left untouched.

    This is similar to ``test_pad_and_write`` in ``test_shell_evaluator``
    but verifies the pycon round-trip (pycon → python → python → pycon)
    is lossless.
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

    evaluator = _make_pycon_evaluator(
        args=["true"],
        write_to_file=True,
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


@pytest.mark.parametrize(
    argnames="pycon_block",
    argvalues=[
        pytest.param(
            textwrap.dedent(
                text="""\
                >>>
                >>> def foo():
                ...     return 1
                ...
                """,
            ),
            id="bare_prompts_and_continuation",
        ),
        pytest.param(
            textwrap.dedent(
                text="""\
                >>> def foo():
                ...     return 1
                >>> foo()
                1
                """,
            ),
            id="continuation_lines_with_output",
        ),
        pytest.param(
            textwrap.dedent(
                text="""\
                >>> def foo():
                ...     return 1
                ...
                >>> foo()
                1
                """,
            ),
            id="trailing_bare_continuation_prompt",
        ),
        pytest.param(
            textwrap.dedent(
                text="""\
                >>>
                >>> x = 1
                """,
            ),
            id="bare_primary_prompt_spacing",
        ),
        pytest.param(
            textwrap.dedent(
                text="""\
                >>> # comment about x
                >>> x = 1
                1
                """,
            ),
            id="comment_lines",
        ),
        pytest.param(
            textwrap.dedent(
                text="""\
                >>> x = 1; y = 2
                """,
            ),
            id="semicolon_no_duplication",
        ),
        pytest.param(
            textwrap.dedent(
                text="""\
                >>> @staticmethod
                ... def foo():
                ...     return 1
                >>> foo()
                1
                """,
            ),
            id="decorated_function",
        ),
    ],
)
def test_write_to_file_round_trip(
    *,
    tmp_path: Path,
    pycon_block: str,
) -> None:
    """Pycon content round-trips unchanged through write-to-file."""
    content = f"```pycon\n{pycon_block}```\n"
    test_file = tmp_path / "test.md"
    test_file.write_text(data=content, encoding="utf-8")

    evaluator = _make_pycon_evaluator(
        args=["true"],
        write_to_file=True,
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
    assert result == content


@pytest.mark.parametrize(
    argnames=("pycon_block", "expected_match"),
    argvalues=[
        pytest.param(
            textwrap.dedent(
                text="""\
                leading output
                ... stray continuation
                >>> x = 1
                1
                """,
            ),
            "leading output",
            id="lines_before_first_prompt",
        ),
        pytest.param(
            textwrap.dedent(
                text="""\
                just output
                ... stray continuation
                """,
            ),
            "just output",
            id="no_prompts_with_stray_lines",
        ),
        pytest.param(
            "\n>>> x = 1\n",
            "appears before the first",
            id="blank_line_before_first_prompt",
        ),
    ],
)
def test_invalid_pycon_raises(
    *,
    tmp_path: Path,
    pycon_block: str,
    expected_match: str,
) -> None:
    """Invalid pycon content raises InvalidPyconError."""
    content = f"```pycon\n{pycon_block}```\n"
    test_file = tmp_path / "test.md"
    test_file.write_text(data=content, encoding="utf-8")

    evaluator = _make_pycon_evaluator(
        args=["true"],
        write_to_file=True,
    )
    parser = SybilMarkdownCodeBlockParser(
        language="pycon",
        evaluator=evaluator,
    )
    sybil = Sybil(parsers=[parser])
    document = sybil.parse(path=test_file)
    (example,) = document.examples()
    with pytest.raises(
        expected_exception=InvalidPyconError,
        match=expected_match,
    ):
        example.evaluate()


def test_write_to_file_syntax_error_fallback(
    *,
    tmp_path: Path,
) -> None:
    """When a formatter produces invalid Python, lines are prefixed
    with ``>>>``.
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

    script = tmp_path / "corrupt.py"
    script.write_text(
        data=textwrap.dedent(
            text="""\
            import sys, pathlib
            path = pathlib.Path(sys.argv[1])
            path.write_text("def (\\n")
            """,
        ),
        encoding="utf-8",
    )

    evaluator = _make_pycon_evaluator(
        args=["python3", str(object=script)],
        write_to_file=True,
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
    assert result == textwrap.dedent(
        text="""\
        ```pycon
        >>> def (
        ```
        """,
    )


def test_write_to_file_statement_count_mismatch(
    *,
    tmp_path: Path,
) -> None:
    """When the formatter changes the number of statements, output
    lines are not preserved.
    """
    content = textwrap.dedent(
        text="""\
        ```pycon
        >>> x = 1
        >>> y = 2
        2
        ```
        """,
    )
    test_file = tmp_path / "test.md"
    test_file.write_text(data=content, encoding="utf-8")

    script = tmp_path / "merge.py"
    script.write_text(
        data=textwrap.dedent(
            text="""\
            import sys, pathlib
            path = pathlib.Path(sys.argv[1])
            path.write_text("z = 3\\n")
            """,
        ),
        encoding="utf-8",
    )

    evaluator = _make_pycon_evaluator(
        args=["python3", str(object=script)],
        write_to_file=True,
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
    assert result == textwrap.dedent(
        text="""\
        ```pycon
        >>> z = 3
        ```
        """,
    )


def test_write_to_file_preserves_output_when_formatter_adds_blank_line(
    *,
    tmp_path: Path,
) -> None:
    """Output is preserved when a formatter adds blank lines between
    statements (e.g. after imports).
    """
    content = textwrap.dedent(
        text="""\
        ```pycon
        >>> import os
        >>> result = os.path.join("foo","bar","baz")
        >>> result
        'foo/bar/baz'
        ```
        """,
    )
    test_file = tmp_path / "test.md"
    test_file.write_text(data=content, encoding="utf-8")

    # Simulate a formatter that adds a blank line after import and
    # re-formats the arguments.
    script = tmp_path / "fmt.py"
    script.write_text(
        data=textwrap.dedent(
            text="""\
            import sys, pathlib
            path = pathlib.Path(sys.argv[1])
            text = path.read_text()
            text = text.replace(
                'import os\\nresult',
                'import os\\n\\nresult',
            )
            text = text.replace(
                '"foo","bar","baz"',
                '"foo", "bar", "baz"',
            )
            path.write_text(text)
            """,
        ),
        encoding="utf-8",
    )

    evaluator = _make_pycon_evaluator(
        args=["python3", str(object=script)],
        write_to_file=True,
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
    assert result == textwrap.dedent(
        text="""\
        ```pycon
        >>> import os
        >>>
        >>> result = os.path.join("foo", "bar", "baz")
        >>> result
        'foo/bar/baz'
        ```
        """,
    )
