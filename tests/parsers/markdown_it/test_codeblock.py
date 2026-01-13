"""
Tests for the markdown_it CodeBlockParser.
"""

from pathlib import Path

import pytest
from sybil import Sybil

from sybil_extras.evaluators.no_op import NoOpEvaluator
from sybil_extras.parsers.markdown_it.codeblock import CodeBlockParser


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
    # Just the opening fence with no content or newline.
    # This creates a single line where start_line=0 and line_offsets=[0].
    # Accessing line_offsets[1] would be out of bounds.
    content = "```python"
    test_file = tmp_path / "test.md"
    test_file.write_text(data=content, encoding="utf-8")

    parser = CodeBlockParser(language="python", evaluator=NoOpEvaluator())
    sybil = Sybil(parsers=[parser])
    document = sybil.parse(path=test_file)
    # Should not raise IndexError
    examples = list(document.examples())

    # The parser should still find the code block (even if empty)
    assert len(examples) == 1


def test_code_block_with_empty_info_string(tmp_path: Path) -> None:
    """Code blocks with no language specified are matched when language=None.

    When a code block has an empty info string (just ```), the pattern
    won't match and block_language should be set to empty string.
    """
    content = "```\nsome code\n```\n"
    test_file = tmp_path / "test.md"
    test_file.write_text(data=content, encoding="utf-8")

    # Parser with no language filter should match all code blocks
    parser = CodeBlockParser(evaluator=NoOpEvaluator())
    sybil = Sybil(parsers=[parser])
    document = sybil.parse(path=test_file)
    examples = list(document.examples())

    assert len(examples) == 1
    # The language lexeme should be empty string
    assert examples[0].region.lexemes["language"] == ""


def test_language_filter_skips_non_matching(tmp_path: Path) -> None:
    """Code blocks with a different language are skipped.

    When a specific language is requested, code blocks with a different
    language should not be matched.
    """
    content = "```javascript\nconsole.log('hello');\n```\n"
    test_file = tmp_path / "test.md"
    test_file.write_text(data=content, encoding="utf-8")

    # Parser looking for Python, but the block is JavaScript
    parser = CodeBlockParser(language="python", evaluator=NoOpEvaluator())
    sybil = Sybil(parsers=[parser])
    document = sybil.parse(path=test_file)
    examples = list(document.examples())

    # Should find no matching code blocks
    assert len(examples) == 0


def test_code_block_inside_blockquote(tmp_path: Path) -> None:
    """Code blocks inside blockquotes are recognized and parsed.

    This tests the fix for
    https://github.com/simplistix/sybil/issues/160.
    MarkdownIt correctly parses fenced code blocks inside blockquotes and
    strips the blockquote prefixes from the content.
    """
    content = """> Here's a quoted code block:
>
> ```python
> def hello() -> None:
>     print("Hello")
> ```
"""
    test_file = tmp_path / "test.md"
    test_file.write_text(data=content, encoding="utf-8")

    parser = CodeBlockParser(language="python", evaluator=NoOpEvaluator())
    sybil = Sybil(parsers=[parser])
    document = sybil.parse(path=test_file)
    examples = list(document.examples())

    assert len(examples) == 1
    # The content should have blockquote prefixes stripped
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

    # Create parser without an evaluator
    parser = CodeBlockParser(language="python")
    sybil = Sybil(parsers=[parser])
    document = sybil.parse(path=test_file)
    examples = list(document.examples())

    assert len(examples) == 1
    # The region should have a non-None evaluator
    assert examples[0].region.evaluator is not None

    # Calling evaluate should raise NotImplementedError (default behavior)
    with pytest.raises(expected_exception=NotImplementedError):
        examples[0].evaluate()
