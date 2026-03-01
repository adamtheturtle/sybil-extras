"""Tests for the myst_parser lexers."""

from pathlib import Path

from sybil import Sybil
from sybil.evaluators.python import PythonEvaluator

from sybil_extras.parsers.myst_parser.codeblock import CodeBlockParser
from sybil_extras.parsers.myst_parser.custom_directive_skip import (
    CustomDirectiveSkipParser,
)


def test_html_directive_at_eof_without_trailing_newline(
    tmp_path: Path,
) -> None:
    """HTML comment directive at end of file without trailing newline
    is recognized.
    """
    content = "<!--- custom-skip: next -->"
    test_file = tmp_path / "test.md"
    test_file.write_text(data=content, encoding="utf-8")

    skip_parser = CustomDirectiveSkipParser(directive="custom-skip")
    sybil = Sybil(parsers=[skip_parser])
    document = sybil.parse(path=test_file)
    examples = list(document.examples())

    assert len(examples) == 1


def test_html_directive_in_indented_section(tmp_path: Path) -> None:
    """HTML comment directives indented by 4+ spaces should be
    recognized.

    By default, MarkdownIt treats 4-space indented content as a
    code_block. The DirectiveInHTMLCommentLexer disables this rule so
    that indented HTML comments are parsed as html_block tokens instead,
    allowing directives to be found in indented sections.
    """
    content = """\
    <!--- custom-skip: next -->

```python
x = 1
```
"""
    test_file = tmp_path / "test.md"
    test_file.write_text(data=content, encoding="utf-8")

    skip_parser = CustomDirectiveSkipParser(directive="custom-skip")
    code_parser = CodeBlockParser(
        language="python",
        evaluator=PythonEvaluator(),
    )
    sybil = Sybil(parsers=[code_parser, skip_parser])
    document = sybil.parse(path=test_file)

    for example in document.examples():
        example.evaluate()

    assert "x" not in document.namespace


def test_percent_comment_directive(tmp_path: Path) -> None:
    """Percent-style comment directives are recognized.

    MyST supports percent-style comments (% comment) as an alternative
    to HTML comments. The myst-parser module should handle both styles.
    """
    content = """\
% custom-skip: next

```python
x = 1
```
"""
    test_file = tmp_path / "test.md"
    test_file.write_text(data=content, encoding="utf-8")

    skip_parser = CustomDirectiveSkipParser(directive="custom-skip")
    code_parser = CodeBlockParser(
        language="python",
        evaluator=PythonEvaluator(),
    )
    sybil = Sybil(parsers=[code_parser, skip_parser])
    document = sybil.parse(path=test_file)

    for example in document.examples():
        example.evaluate()

    assert "x" not in document.namespace


def test_percent_comment_directive_at_eof(tmp_path: Path) -> None:
    """Percent-style comment directive at end of file is recognized."""
    content = "% custom-skip: next"
    test_file = tmp_path / "test.md"
    test_file.write_text(data=content, encoding="utf-8")

    skip_parser = CustomDirectiveSkipParser(directive="custom-skip")
    sybil = Sybil(parsers=[skip_parser])
    document = sybil.parse(path=test_file)
    examples = list(document.examples())

    assert len(examples) == 1
