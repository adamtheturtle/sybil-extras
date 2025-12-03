"""
Tests for the MDX grouped source parser.
"""

from pathlib import Path

from sybil import Sybil
from sybil.example import Example

from sybil_extras.parsers.mdx.codeblock import CodeBlockParser
from sybil_extras.parsers.mdx.grouped_source import (
    GroupAttributeParser,
    GroupedSourceParser,
)


def test_html_comment_grouping(tmp_path: Path) -> None:
    """
    Test grouping code blocks using HTML comment directives.
    """
    content = """\
```python
x = []
```

<!--- group: start -->

```python
x = [*x, 1]
```

```python
x = [*x, 2]
```

<!--- group: end -->

```python
x = [*x, 3]
```
"""
    test_document = tmp_path / "test.mdx"
    test_document.write_text(data=content, encoding="utf-8")

    def evaluator(example: Example) -> None:
        """
        Add code block content to the namespace.
        """
        existing_blocks = example.document.namespace.get("blocks", [])
        example.document.namespace["blocks"] = [
            *existing_blocks,
            example.parsed,
        ]

    group_parser = GroupedSourceParser(
        directive="group",
        evaluator=evaluator,
        pad_groups=True,
    )
    code_block_parser = CodeBlockParser(language="python", evaluator=evaluator)

    sybil = Sybil(parsers=[code_block_parser, group_parser])
    document = sybil.parse(path=test_document)

    for example in document.examples():
        example.evaluate()

    # First block ungrouped, second/third grouped, fourth ungrouped
    expected_block_count = 3
    assert len(document.namespace["blocks"]) == expected_block_count
    assert document.namespace["blocks"][0] == "x = []\n"
    assert "x = [*x, 1]" in document.namespace["blocks"][1]
    assert "x = [*x, 2]" in document.namespace["blocks"][1]
    assert document.namespace["blocks"][2] == "x = [*x, 3]\n"


def test_group_attribute_basic(tmp_path: Path) -> None:
    """
    Test grouping code blocks using the group attribute.
    """
    content = """\
```python group="setup"
x = 1
```

Some text here.

```python group="setup"
y = 2
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

    group_parser = GroupAttributeParser(
        evaluator=evaluator,
        pad_groups=False,
        language="python",
    )

    sybil = Sybil(parsers=[group_parser])
    document = sybil.parse(path=test_document)

    for example in document.examples():
        example.evaluate()

    # Should have one combined block for the "setup" group
    assert len(collected_blocks) == 1
    assert "x = 1" in collected_blocks[0]
    assert "y = 2" in collected_blocks[0]
    # The ungrouped block should not be in the grouped result
    assert "z = 3" not in collected_blocks[0]


def test_multiple_groups(tmp_path: Path) -> None:
    """
    Test multiple different groups in the same document.
    """
    content = """\
```python group="setup"
x = 1
```

```python group="test"
assert x == 1
```

```python group="setup"
y = 2
```

```python group="test"
assert y == 2
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

    group_parser = GroupAttributeParser(
        evaluator=evaluator,
        pad_groups=False,
        language="python",
    )

    sybil = Sybil(parsers=[group_parser])
    document = sybil.parse(path=test_document)

    for example in document.examples():
        example.evaluate()

    # Should have two combined blocks, one for each group
    expected_block_count = 2
    assert len(collected_blocks) == expected_block_count

    # Find the setup and test blocks
    setup_block = next(b for b in collected_blocks if "x = 1" in b)
    test_block = next(b for b in collected_blocks if "assert x == 1" in b)

    assert "x = 1" in setup_block
    assert "y = 2" in setup_block
    assert "assert x == 1" in test_block
    assert "assert y == 2" in test_block


def test_group_attribute_with_padding(tmp_path: Path) -> None:
    """
    Test that padding preserves line numbers.
    """
    content = """\
```python group="main"
x = 1
```

Line 2
Line 3
Line 4

```python group="main"
y = 2
```
"""
    test_document = tmp_path / "test.mdx"
    test_document.write_text(data=content, encoding="utf-8")

    def evaluator(example: Example) -> None:
        """
        Store the combined code.
        """
        example.document.namespace["code"] = example.parsed

    group_parser = GroupAttributeParser(
        evaluator=evaluator,
        pad_groups=True,
        language="python",
    )

    sybil = Sybil(parsers=[group_parser])
    document = sybil.parse(path=test_document)

    for example in document.examples():
        example.evaluate()

    combined_code = document.namespace["code"]

    # With padding enabled, there should be newlines between the blocks
    assert "x = 1" in combined_code
    assert "y = 2" in combined_code
    assert "\n\n" in combined_code  # Multiple newlines for padding


def test_mixed_languages_with_group(tmp_path: Path) -> None:
    """
    Test that language filtering works with group attributes.
    """
    content = """\
```python group="setup"
x = 1
```

```javascript group="setup"
const y = 2;
```

```python group="setup"
z = 3
```
"""
    test_document = tmp_path / "test.mdx"
    test_document.write_text(data=content, encoding="utf-8")

    def evaluator(example: Example) -> None:
        """
        Store the combined code.
        """
        example.document.namespace["code"] = example.parsed

    # Only group Python blocks
    group_parser = GroupAttributeParser(
        evaluator=evaluator,
        pad_groups=False,
        language="python",
    )

    sybil = Sybil(parsers=[group_parser])
    document = sybil.parse(path=test_document)

    for example in document.examples():
        example.evaluate()

    combined_code = document.namespace["code"]

    # Should only have Python blocks
    assert "x = 1" in combined_code
    assert "z = 3" in combined_code
    # JavaScript block should not be included
    assert "const y" not in combined_code


def test_group_attribute_all_languages(tmp_path: Path) -> None:
    """
    Test grouping blocks of all languages when language is None.
    """
    content = """\
```python group="mixed"
x = 1
```

```javascript group="mixed"
const y = 2;
```
"""
    test_document = tmp_path / "test.mdx"
    test_document.write_text(data=content, encoding="utf-8")

    def evaluator(example: Example) -> None:
        """
        Store the combined code.
        """
        example.document.namespace["code"] = example.parsed

    # Group all languages
    group_parser = GroupAttributeParser(
        evaluator=evaluator,
        pad_groups=False,
        language=None,
    )

    sybil = Sybil(parsers=[group_parser])
    document = sybil.parse(path=test_document)

    for example in document.examples():
        example.evaluate()

    combined_code = document.namespace["code"]

    # Should have both Python and JavaScript
    assert "x = 1" in combined_code
    assert "const y = 2" in combined_code


def test_no_padding(tmp_path: Path) -> None:
    """
    Test HTML comment grouping without padding.
    """
    content = """\
<!--- group: start -->

```python
x = 1
```

```python
y = 2
```

<!--- group: end -->
"""
    test_document = tmp_path / "test.mdx"
    test_document.write_text(data=content, encoding="utf-8")

    def evaluator(example: Example) -> None:
        """
        Store the combined code.
        """
        example.document.namespace["code"] = example.parsed

    group_parser = GroupedSourceParser(
        directive="group",
        evaluator=evaluator,
        pad_groups=False,
    )
    code_block_parser = CodeBlockParser(language="python", evaluator=evaluator)

    sybil = Sybil(parsers=[code_block_parser, group_parser])
    document = sybil.parse(path=test_document)

    for example in document.examples():
        example.evaluate()

    combined_code = document.namespace["code"]

    # Without padding, blocks should be separated by a single newline
    lines = combined_code.split("\n")
    # Count empty lines between code blocks
    empty_line_count = sum(1 for line in lines if line == "")
    # Should have minimal empty lines with pad_groups=False
    # At most one separator newline plus trailing
    max_empty_lines = 2
    assert empty_line_count <= max_empty_lines
