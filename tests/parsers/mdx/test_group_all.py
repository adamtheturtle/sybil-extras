"""
Tests for the MDX group all parser.
"""

from pathlib import Path

from sybil import Sybil
from sybil.example import Example

from sybil_extras.parsers.mdx.codeblock import CodeBlockParser
from sybil_extras.parsers.mdx.group_all import GroupAllParser


def test_group_all_basic(tmp_path: Path) -> None:
    """
    Test that all code blocks are grouped into a single execution.
    """
    content = """\
```python
x = 1
```

```python
y = 2
```

```python
z = x + y
assert z == 3
```
"""
    test_document = tmp_path / "test.mdx"
    test_document.write_text(data=content, encoding="utf-8")

    namespace: dict[str, int] = {}

    def evaluator(example: Example) -> None:
        """
        Execute the code in a shared namespace.
        """
        exec(example.parsed, namespace)  # noqa: S102

    code_block_parser = CodeBlockParser(language="python", evaluator=evaluator)
    group_all_parser = GroupAllParser(
        evaluator=evaluator,
        pad_groups=True,
    )

    sybil = Sybil(parsers=[code_block_parser, group_all_parser])
    document = sybil.parse(path=test_document)

    for example in document.examples():
        example.evaluate()

    # Variables should be available across all blocks
    assert namespace["x"] == 1
    assert namespace["y"] == 2  # noqa: PLR2004
    assert namespace["z"] == 3  # noqa: PLR2004


def test_group_all_empty_document(tmp_path: Path) -> None:
    """
    Test that group all parser handles documents without code blocks.
    """
    content = """\
# Just a heading

Some text without code blocks.
"""
    test_document = tmp_path / "test.mdx"
    test_document.write_text(data=content, encoding="utf-8")

    def evaluator(example: Example) -> None:
        """
        This should not be called.
        """
        example.document.namespace["called"] = True

    code_block_parser = CodeBlockParser(language="python", evaluator=evaluator)
    group_all_parser = GroupAllParser(
        evaluator=evaluator,
        pad_groups=True,
    )

    sybil = Sybil(parsers=[code_block_parser, group_all_parser])
    document = sybil.parse(path=test_document)

    for example in document.examples():
        example.evaluate()

    # Evaluator should not have been called for code blocks
    assert "called" not in document.namespace


def test_group_all_with_no_padding(tmp_path: Path) -> None:
    """
    Test group all parser without padding between blocks.
    """
    content = """\
```python
def foo():
    return 1
```

```python
def bar():
    return 2
```

```python
result = foo() + bar()
assert result == 3
```
"""
    test_document = tmp_path / "test.mdx"
    test_document.write_text(data=content, encoding="utf-8")

    namespace: dict[str, int] = {}

    def evaluator(example: Example) -> None:
        """
        Execute the code in a shared namespace.
        """
        exec(example.parsed, namespace)  # noqa: S102

    code_block_parser = CodeBlockParser(language="python", evaluator=evaluator)
    group_all_parser = GroupAllParser(
        evaluator=evaluator,
        pad_groups=False,
    )

    sybil = Sybil(parsers=[code_block_parser, group_all_parser])
    document = sybil.parse(path=test_document)

    for example in document.examples():
        example.evaluate()

    # Functions should be defined and callable
    assert namespace["result"] == 3  # noqa: PLR2004


def test_group_all_multiple_languages(tmp_path: Path) -> None:
    """
    Test that group all works with multiple languages.
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

    # Parse only Python blocks
    code_block_parser = CodeBlockParser(language="python", evaluator=evaluator)
    group_all_parser = GroupAllParser(
        evaluator=evaluator,
        pad_groups=True,
    )

    sybil = Sybil(parsers=[code_block_parser, group_all_parser])
    document = sybil.parse(path=test_document)

    for example in document.examples():
        example.evaluate()

    # Should have one combined block with only Python blocks
    assert len(collected_blocks) == 1
    assert "x = 1" in collected_blocks[0]
    assert "z = 3" in collected_blocks[0]
    # JavaScript block should not be included
    assert "const y" not in collected_blocks[0]


def test_group_all_with_attributes(tmp_path: Path) -> None:
    """
    Test that group all works with MDX code blocks that have attributes.
    """
    content = """\
```python title="setup.py"
x = 1
```

```python title="test.py"
assert x == 1
```
"""
    test_document = tmp_path / "test.mdx"
    test_document.write_text(data=content, encoding="utf-8")

    namespace: dict[str, int] = {}

    def evaluator(example: Example) -> None:
        """
        Execute the code in a shared namespace.
        """
        exec(example.parsed, namespace)  # noqa: S102

    code_block_parser = CodeBlockParser(language="python", evaluator=evaluator)
    group_all_parser = GroupAllParser(
        evaluator=evaluator,
        pad_groups=True,
    )

    sybil = Sybil(parsers=[code_block_parser, group_all_parser])
    document = sybil.parse(path=test_document)

    for example in document.examples():
        example.evaluate()

    # Both blocks should execute successfully
    assert namespace["x"] == 1
