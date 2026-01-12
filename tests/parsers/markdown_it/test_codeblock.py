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
