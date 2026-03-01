"""Tests for the myst_parser CodeBlockParser."""

import textwrap
from pathlib import Path

import pytest
from sybil import Sybil

from sybil_extras.evaluators.no_op import NoOpEvaluator
from sybil_extras.parsers.myst_parser.codeblock import CodeBlockParser


def test_language_with_extra_info(tmp_path: Path) -> None:
    """Code blocks with extra info after the language are matched.

    For example, ```python title="example" should match language="python".
    The info line from MarkdownIt includes the full content after the fence
    markers, so we need to extract only the first word as the language.
    """
    content = '```python title="example"\nprint("hello")\n```\n'
    test_file = tmp_path / "test.md"
    test_file.write_text(data=content, encoding="utf-8")

    parser = CodeBlockParser(language="python", evaluator=NoOpEvaluator())
    sybil = Sybil(parsers=[parser])
    document = sybil.parse(path=test_file)
    examples = list(document.examples())

    assert len(examples) == 1
    assert examples[0].parsed.text == 'print("hello")\n'


def test_unclosed_fence_no_trailing_newline(tmp_path: Path) -> None:
    """Documents with unclosed fenced code blocks and no trailing newline
    should not cause an IndexError.

    When start_line + 1 exceeds the line_offsets array length, the
    parser should handle it gracefully.
    """
    content = "```python"
    test_file = tmp_path / "test.md"
    test_file.write_text(data=content, encoding="utf-8")

    parser = CodeBlockParser(language="python", evaluator=NoOpEvaluator())
    sybil = Sybil(parsers=[parser])
    document = sybil.parse(path=test_file)
    examples = list(document.examples())

    assert len(examples) == 1


def test_code_block_with_empty_info_string(tmp_path: Path) -> None:
    """Code blocks with no language specified are matched when
    language=None.

    When a code block has an empty info string (just ```), the pattern
    won't match and block_language should be set to empty string.
    """
    content = "```\nsome code\n```\n"
    test_file = tmp_path / "test.md"
    test_file.write_text(data=content, encoding="utf-8")

    parser = CodeBlockParser(evaluator=NoOpEvaluator())
    sybil = Sybil(parsers=[parser])
    document = sybil.parse(path=test_file)
    examples = list(document.examples())

    assert len(examples) == 1
    assert examples[0].region.lexemes["language"] == ""


def test_language_filter_skips_non_matching(tmp_path: Path) -> None:
    """Code blocks with a different language are skipped.

    When a specific language is requested, code blocks with a different
    language should not be matched.
    """
    content = "```javascript\nconsole.log('hello');\n```\n"
    test_file = tmp_path / "test.md"
    test_file.write_text(data=content, encoding="utf-8")

    parser = CodeBlockParser(language="python", evaluator=NoOpEvaluator())
    sybil = Sybil(parsers=[parser])
    document = sybil.parse(path=test_file)
    examples = list(document.examples())

    assert len(examples) == 0


def test_code_block_inside_blockquote(tmp_path: Path) -> None:
    """Code blocks inside blockquotes are recognized and parsed.

    The myst-parser correctly parses fenced code blocks inside
    blockquotes and strips the blockquote prefixes from the content.
    """
    content = textwrap.dedent(
        text="""\
        > Here's a quoted code block:
        >
        > ```python
        > def hello() -> None:
        >     print("Hello")
        > ```
        """
    )
    test_file = tmp_path / "test.md"
    test_file.write_text(data=content, encoding="utf-8")

    parser = CodeBlockParser(language="python", evaluator=NoOpEvaluator())
    sybil = Sybil(parsers=[parser])
    document = sybil.parse(path=test_file)
    examples = list(document.examples())

    assert len(examples) == 1
    assert (
        examples[0].parsed.text == 'def hello() -> None:\n    print("Hello")\n'
    )
    assert examples[0].region.lexemes["language"] == "python"


def test_evaluator_not_none_when_omitted(tmp_path: Path) -> None:
    """When no evaluator is provided, the region still has an evaluator.

    Sybil's Example.evaluate() does nothing when region.evaluator is
    None. To work correctly with document evaluators (like
    GroupAllParser), the region must have a non-None evaluator. Like
    Sybil's AbstractCodeBlockParser, we provide a default evaluate
    method that raises NotImplementedError.
    """
    content = "```python\nprint('hello')\n```\n"
    test_file = tmp_path / "test.md"
    test_file.write_text(data=content, encoding="utf-8")

    parser = CodeBlockParser(language="python")
    sybil = Sybil(parsers=[parser])
    document = sybil.parse(path=test_file)
    examples = list(document.examples())

    assert len(examples) == 1
    assert examples[0].region.evaluator is not None

    with pytest.raises(expected_exception=NotImplementedError):
        examples[0].evaluate()


def test_percent_comment_does_not_break_parsing(tmp_path: Path) -> None:
    """Percent-style comments are handled by myst-parser.

    The myst-parser understands percent comments natively, so they
    should not interfere with code block parsing.
    """
    content = textwrap.dedent(
        text="""\
        % This is a MyST comment

        ```python
        x = 1
        ```

        % Another comment

        ```python
        y = 2
        ```
        """
    )
    test_file = tmp_path / "test.md"
    test_file.write_text(data=content, encoding="utf-8")

    parser = CodeBlockParser(language="python", evaluator=NoOpEvaluator())
    sybil = Sybil(parsers=[parser])
    document = sybil.parse(path=test_file)
    examples = list(document.examples())

    expected_count = 2
    assert len(examples) == expected_count
    assert examples[0].parsed.text == "x = 1\n"
    assert examples[1].parsed.text == "y = 2\n"


@pytest.mark.parametrize(
    argnames="directive",
    argvalues=["code-block", "code", "code-cell"],
)
def test_myst_directive_code_block(*, tmp_path: Path, directive: str) -> None:
    """MyST directive-style code blocks are matched by language.

    Blocks in the form ```{directive} language``` extract the language
    from the second word of the info string, so they are matched when
    that language is requested.
    """
    content = textwrap.dedent(
        text=f"""\
        ```{{{directive}}} python
        print('hello')
        ```
        """,
    )
    test_file = tmp_path / "test.md"
    test_file.write_text(data=content, encoding="utf-8")

    parser = CodeBlockParser(language="python", evaluator=NoOpEvaluator())
    sybil = Sybil(parsers=[parser])
    document = sybil.parse(path=test_file)
    examples = list(document.examples())

    assert len(examples) == 1
    assert examples[0].parsed.text == "print('hello')\n"
    assert examples[0].region.lexemes["language"] == "python"


@pytest.mark.parametrize(
    argnames="directive",
    argvalues=["code-block", "code", "code-cell"],
)
def test_myst_directive_code_block_no_language(
    *,
    tmp_path: Path,
    directive: str,
) -> None:
    """MyST directive-style code blocks with no language are not matched.

    When a specific language is requested, a directive block with no
    language argument (e.g., ```{code-block}```) is not matched.
    """
    content = textwrap.dedent(
        text=f"""\
        ```{{{directive}}}
        print('hello')
        ```
        """,
    )
    test_file = tmp_path / "test.md"
    test_file.write_text(data=content, encoding="utf-8")

    parser = CodeBlockParser(language="python", evaluator=NoOpEvaluator())
    sybil = Sybil(parsers=[parser])
    document = sybil.parse(path=test_file)
    examples = list(document.examples())

    assert len(examples) == 0


@pytest.mark.parametrize(
    argnames="directive",
    argvalues=["code-block", "code", "code-cell"],
)
def test_myst_directive_code_block_wrong_language(
    *,
    tmp_path: Path,
    directive: str,
) -> None:
    """MyST directive-style code blocks with a different language are
    skipped.

    When a specific language is requested, a directive block specifying
    a different language is not matched.
    """
    content = textwrap.dedent(
        text=f"""\
        ```{{{directive}}} javascript
        console.log('hi');
        ```
        """,
    )
    test_file = tmp_path / "test.md"
    test_file.write_text(data=content, encoding="utf-8")

    parser = CodeBlockParser(language="python", evaluator=NoOpEvaluator())
    sybil = Sybil(parsers=[parser])
    document = sybil.parse(path=test_file)
    examples = list(document.examples())

    assert len(examples) == 0
