"""
Tests for the MDX code block parser.
"""

from pathlib import Path

from sybil import Sybil
from sybil.example import Example
from sybil.testing import check_parser

from sybil_extras.parsers.mdx.codeblock import CodeBlockParser


def test_basic_codeblock() -> None:
    """
    Test parsing a basic MDX code block without attributes.
    """
    content = """\
```python
x = 1
print(x)
```
"""

    def evaluator(example: Example) -> None:
        """
        Store the parsed code in the namespace.
        """
        example.document.namespace["code"] = example.parsed

    parser = CodeBlockParser(language="python", evaluator=evaluator)
    document = check_parser(parser=parser, text=content)

    assert document.namespace["code"] == "x = 1\nprint(x)\n"


def test_codeblock_with_title() -> None:
    """
    Test parsing an MDX code block with a title attribute.
    """
    content = """\
```python title="hello.py"
print("hello")
```
"""

    def evaluator(example: Example) -> None:
        """
        Store the parsed code and attributes in the namespace.
        """
        example.document.namespace["code"] = example.parsed
        example.document.namespace["attributes"] = example.region.lexemes.get(
            "attributes", {}
        )

    parser = CodeBlockParser(language="python", evaluator=evaluator)
    document = check_parser(parser=parser, text=content)

    assert document.namespace["code"] == 'print("hello")\n'
    assert document.namespace["attributes"] == {"title": "hello.py"}


def test_codeblock_with_multiple_attributes() -> None:
    """
    Test parsing an MDX code block with multiple attributes.
    """
    content = """\
```python title="script.py" group="main"
x = 1
y = 2
```
"""

    def evaluator(example: Example) -> None:
        """
        Store the parsed code and attributes in the namespace.
        """
        example.document.namespace["code"] = example.parsed
        example.document.namespace["attributes"] = example.region.lexemes.get(
            "attributes", {}
        )

    parser = CodeBlockParser(language="python", evaluator=evaluator)
    document = check_parser(parser=parser, text=content)

    assert document.namespace["code"] == "x = 1\ny = 2\n"
    assert document.namespace["attributes"] == {
        "title": "script.py",
        "group": "main",
    }


def test_multiple_codeblocks(tmp_path: Path) -> None:
    """
    Test parsing multiple MDX code blocks.
    """
    content = """\
```python title="first.py"
x = 1
```

Some text here.

```python title="second.py"
y = 2
```
"""
    test_document = tmp_path / "test.mdx"
    test_document.write_text(data=content, encoding="utf-8")

    collected_blocks: list[tuple[str, dict[str, str]]] = []

    def evaluator(example: Example) -> None:
        """
        Collect all parsed code blocks.
        """
        code = example.parsed
        attributes = example.region.lexemes.get("attributes", {})
        collected_blocks.append((code, attributes))

    parser = CodeBlockParser(language="python", evaluator=evaluator)
    sybil = Sybil(parsers=[parser])
    document = sybil.parse(path=test_document)

    for example in document.examples():
        example.evaluate()

    expected_block_count = 2
    assert len(collected_blocks) == expected_block_count
    assert collected_blocks[0] == ("x = 1\n", {"title": "first.py"})
    assert collected_blocks[1] == ("y = 2\n", {"title": "second.py"})


def test_language_filtering(tmp_path: Path) -> None:
    """
    Test that the parser only matches the specified language.
    """
    content = """\
```python
x = 1
```

```javascript
const y = 2;
```

```python
z = 3
```
"""
    test_document = tmp_path / "test.mdx"
    test_document.write_text(data=content, encoding="utf-8")

    collected_blocks: list[str] = []

    def evaluator(example: Example) -> None:
        """
        Collect all parsed code blocks.
        """
        collected_blocks.append(example.parsed)

    parser = CodeBlockParser(language="python", evaluator=evaluator)
    sybil = Sybil(parsers=[parser])
    document = sybil.parse(path=test_document)

    for example in document.examples():
        example.evaluate()

    expected_block_count = 2
    assert len(collected_blocks) == expected_block_count
    assert collected_blocks[0] == "x = 1\n"
    assert collected_blocks[1] == "z = 3\n"


def test_no_language_specified(tmp_path: Path) -> None:
    """
    Test parsing code blocks when no language is specified in the parser.
    """
    content = """\
```python
x = 1
```

```javascript
y = 2
```
"""
    test_document = tmp_path / "test.mdx"
    test_document.write_text(data=content, encoding="utf-8")

    collected_blocks: list[str] = []

    def evaluator(example: Example) -> None:
        """
        Collect all parsed code blocks.
        """
        collected_blocks.append(example.parsed)

    parser = CodeBlockParser(language=None, evaluator=evaluator)
    sybil = Sybil(parsers=[parser])
    document = sybil.parse(path=test_document)

    for example in document.examples():
        example.evaluate()

    expected_block_count = 2
    assert len(collected_blocks) == expected_block_count
    assert collected_blocks[0] == "x = 1\n"
    assert collected_blocks[1] == "y = 2\n"


def test_attributes_with_special_characters() -> None:
    """
    Test parsing attributes with special characters in values.
    """
    content = """\
```python title="my-script.py" group="group-1"
x = 1
```
"""

    def evaluator(example: Example) -> None:
        """
        Store the attributes in the namespace.
        """
        example.document.namespace["attributes"] = example.region.lexemes.get(
            "attributes", {}
        )

    parser = CodeBlockParser(language="python", evaluator=evaluator)
    document = check_parser(parser=parser, text=content)

    assert document.namespace["attributes"] == {
        "title": "my-script.py",
        "group": "group-1",
    }


def test_empty_codeblock() -> None:
    """
    Test parsing an empty MDX code block.
    """
    content = """\
```python title="empty.py"
```
"""

    def evaluator(example: Example) -> None:
        """
        Store the parsed code in the namespace.
        """
        example.document.namespace["code"] = example.parsed

    parser = CodeBlockParser(language="python", evaluator=evaluator)
    document = check_parser(parser=parser, text=content)

    assert document.namespace["code"] == ""
