"""
Tests for the MDX lexer using sybil.testing.check_lexer.
"""

import re

from sybil import Lexeme
from sybil.parsers.markdown.lexers import RawFencedCodeBlockLexer
from sybil.testing import check_lexer


def test_basic_python_block() -> None:
    """
    Test lexing a basic Python code block without attributes.
    """
    info_pattern = re.compile(
        r"(?P<language>\w+)(?P<attributes>[^\n]*?)$\n",
        re.MULTILINE,
    )
    lexer = RawFencedCodeBlockLexer(info_pattern=info_pattern, mapping=None)

    check_lexer(
        lexer,
        """\
```python
x = 1
print(x)
```
""",
        expected_text="```python\nx = 1\nprint(x)\n```",
        expected_lexemes={
            "language": "python",
            "attributes": "",
            "source": Lexeme("x = 1\nprint(x)\n", offset=10, line_offset=1),
        },
    )


def test_python_block_with_title() -> None:
    """
    Test lexing a Python code block with a title attribute.
    """
    info_pattern = re.compile(
        r"(?P<language>\w+)(?P<attributes>[^\n]*?)$\n",
        re.MULTILINE,
    )
    lexer = RawFencedCodeBlockLexer(info_pattern=info_pattern, mapping=None)

    check_lexer(
        lexer,
        """\
```python title="hello.py"
print("hello")
```
""",
        expected_text='```python title="hello.py"\nprint("hello")\n```',
        expected_lexemes={
            "language": "python",
            "attributes": ' title="hello.py"',
            "source": Lexeme('print("hello")\n', offset=28, line_offset=1),
        },
    )


def test_python_block_with_multiple_attributes() -> None:
    """
    Test lexing a Python code block with multiple attributes.
    """
    info_pattern = re.compile(
        r"(?P<language>\w+)(?P<attributes>[^\n]*?)$\n",
        re.MULTILINE,
    )
    lexer = RawFencedCodeBlockLexer(info_pattern=info_pattern, mapping=None)

    check_lexer(
        lexer,
        """\
```python title="script.py" group="main"
x = 1
y = 2
```
""",
        expected_text=(
            '```python title="script.py" group="main"\nx = 1\ny = 2\n```'
        ),
        expected_lexemes={
            "language": "python",
            "attributes": ' title="script.py" group="main"',
            "source": Lexeme("x = 1\ny = 2\n", offset=42, line_offset=1),
        },
    )


def test_jsx_block_with_title() -> None:
    """
    Test lexing a JSX code block with a title (Docusaurus-style).
    """
    info_pattern = re.compile(
        r"(?P<language>\w+)(?P<attributes>[^\n]*?)$\n",
        re.MULTILINE,
    )
    lexer = RawFencedCodeBlockLexer(info_pattern=info_pattern, mapping=None)

    check_lexer(
        lexer,
        """\
```jsx title="/src/components/HelloCodeTitle.js"
function HelloCodeTitle(props) {
  return <h1>Hello, {props.name}</h1>;
}
```
""",
        expected_text=(
            '```jsx title="/src/components/HelloCodeTitle.js"\n'
            "function HelloCodeTitle(props) {\n"
            "  return <h1>Hello, {props.name}</h1>;\n"
            "}\n"
            "```"
        ),
        expected_lexemes={
            "language": "jsx",
            "attributes": ' title="/src/components/HelloCodeTitle.js"',
            "source": Lexeme(
                "function HelloCodeTitle(props) {\n"
                "  return <h1>Hello, {props.name}</h1>;\n"
                "}\n",
                offset=51,
                line_offset=1,
            ),
        },
    )


def test_empty_code_block() -> None:
    """
    Test lexing an empty code block.
    """
    info_pattern = re.compile(
        r"(?P<language>\w+)(?P<attributes>[^\n]*?)$\n",
        re.MULTILINE,
    )
    lexer = RawFencedCodeBlockLexer(info_pattern=info_pattern, mapping=None)

    check_lexer(
        lexer,
        """\
```python title="empty.py"
```
""",
        expected_text='```python title="empty.py"\n```',
        expected_lexemes={
            "language": "python",
            "attributes": ' title="empty.py"',
            "source": Lexeme("", offset=28, line_offset=1),
        },
    )


def test_language_specific_lexer() -> None:
    """
    Test lexing with a language-specific pattern.
    """
    info_pattern = re.compile(
        r"(?P<language>python)(?P<attributes>[^\n]*?)$\n",
        re.MULTILINE,
    )
    lexer = RawFencedCodeBlockLexer(info_pattern=info_pattern, mapping=None)

    check_lexer(
        lexer,
        """\
```python group="test"
x = 1
```
""",
        expected_text='```python group="test"\nx = 1\n```',
        expected_lexemes={
            "language": "python",
            "attributes": ' group="test"',
            "source": Lexeme("x = 1\n", offset=24, line_offset=1),
        },
    )
