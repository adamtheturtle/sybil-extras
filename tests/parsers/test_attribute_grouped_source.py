"""
Attribute-based grouped source parser tests for MDX.
"""

from pathlib import Path

from sybil import Sybil

from sybil_extras.evaluators.block_accumulator import BlockAccumulatorEvaluator
from sybil_extras.parsers.mdx.attribute_grouped_source import (
    AttributeGroupedSourceParser,
)
from sybil_extras.parsers.mdx.codeblock import CodeBlockParser


def test_attribute_group_single_group(tmp_path: Path) -> None:
    """
    The attribute group parser groups examples with the same group attribute.
    """
    content = """
```python group="example1"
from pprint import pp
```

Some text in between.

```python group="example1"
pp({"hello": "world"})
```
"""
    test_document = tmp_path / "test.mdx"
    test_document.write_text(data=content, encoding="utf-8")

    evaluator = BlockAccumulatorEvaluator(namespace_key="blocks")
    code_block_parser = CodeBlockParser(language="python")
    group_parser = AttributeGroupedSourceParser(
        code_block_parser=code_block_parser,
        evaluator=evaluator,
        attribute_name="group",
        pad_groups=True,
    )

    sybil = Sybil(parsers=[group_parser])
    document = sybil.parse(path=test_document)

    for example in document.examples():
        example.evaluate()

    # Should have one combined block
    assert len(document.namespace["blocks"]) == 1
    expected = 'from pprint import pp\n\n\n\n\n\npp({"hello": "world"})\n'
    assert document.namespace["blocks"][0] == expected


def test_attribute_group_multiple_groups(tmp_path: Path) -> None:
    """
    Multiple groups are handled separately and in document order.
    """
    content = """
```python group="setup"
x = []
```

```python group="setup"
x = [*x, 1]
```

```python group="example"
y = []
```

```python group="setup"
x = [*x, 2]
```

```python group="example"
y = [*y, 10]
```
"""
    test_document = tmp_path / "test.mdx"
    test_document.write_text(data=content, encoding="utf-8")

    evaluator = BlockAccumulatorEvaluator(namespace_key="blocks")
    code_block_parser = CodeBlockParser(language="python")
    group_parser = AttributeGroupedSourceParser(
        code_block_parser=code_block_parser,
        evaluator=evaluator,
        attribute_name="group",
        pad_groups=True,
    )

    sybil = Sybil(parsers=[group_parser])
    document = sybil.parse(path=test_document)

    for example in document.examples():
        example.evaluate()

    # Should have two combined blocks (setup first, then example)
    expected_num_blocks = 2
    assert len(document.namespace["blocks"]) == expected_num_blocks

    # First group "setup" - appears first in document
    expected_setup = "x = []\n\n\n\nx = [*x, 1]\n\n\n\n\n\n\n\nx = [*x, 2]\n"
    assert document.namespace["blocks"][0] == expected_setup

    # Second group "example" - appears second in document
    expected_example = "y = []\n\n\n\n\n\n\n\ny = [*y, 10]\n"
    assert document.namespace["blocks"][1] == expected_example


def test_attribute_group_no_group_attribute(tmp_path: Path) -> None:
    """
    Code blocks without the group attribute are not grouped.
    """
    content = """
```python
x = 1
```

```python group="example"
y = 2
```

```python
z = 3
```
"""
    test_document = tmp_path / "test.mdx"
    test_document.write_text(data=content, encoding="utf-8")

    evaluator = BlockAccumulatorEvaluator(namespace_key="blocks")
    code_block_parser = CodeBlockParser(language="python")
    group_parser = AttributeGroupedSourceParser(
        code_block_parser=code_block_parser,
        evaluator=evaluator,
        attribute_name="group",
        pad_groups=True,
    )

    sybil = Sybil(parsers=[group_parser])
    document = sybil.parse(path=test_document)

    for example in document.examples():
        example.evaluate()

    # Should have only one block (the one with group="example")
    assert len(document.namespace["blocks"]) == 1
    assert document.namespace["blocks"][0] == "y = 2\n"


def test_attribute_group_custom_attribute_name(tmp_path: Path) -> None:
    """
    Custom attribute names can be used for grouping.
    """
    content = """
```python mygroup="test1"
a = 1
```

```python mygroup="test1"
b = 2
```
"""
    test_document = tmp_path / "test.mdx"
    test_document.write_text(data=content, encoding="utf-8")

    evaluator = BlockAccumulatorEvaluator(namespace_key="blocks")
    code_block_parser = CodeBlockParser(language="python")
    group_parser = AttributeGroupedSourceParser(
        code_block_parser=code_block_parser,
        evaluator=evaluator,
        attribute_name="mygroup",
        pad_groups=True,
    )

    sybil = Sybil(parsers=[group_parser])
    document = sybil.parse(path=test_document)

    for example in document.examples():
        example.evaluate()

    assert len(document.namespace["blocks"]) == 1
    expected = "a = 1\n\n\n\nb = 2\n"
    assert document.namespace["blocks"][0] == expected


def test_attribute_group_with_other_attributes(tmp_path: Path) -> None:
    """
    Code blocks with multiple attributes still group correctly.
    """
    content = """
```python title="example.py" group="setup" showLineNumbers
value = 7
```

```python group="setup" title="example2.py"
result = value * 2
```
"""
    test_document = tmp_path / "test.mdx"
    test_document.write_text(data=content, encoding="utf-8")

    evaluator = BlockAccumulatorEvaluator(namespace_key="blocks")
    code_block_parser = CodeBlockParser(language="python")
    group_parser = AttributeGroupedSourceParser(
        code_block_parser=code_block_parser,
        evaluator=evaluator,
        attribute_name="group",
        pad_groups=True,
    )

    sybil = Sybil(parsers=[group_parser])
    document = sybil.parse(path=test_document)

    for example in document.examples():
        example.evaluate()

    assert len(document.namespace["blocks"]) == 1
    expected = "value = 7\n\n\n\nresult = value * 2\n"
    assert document.namespace["blocks"][0] == expected


def test_attribute_group_pad_groups_false(tmp_path: Path) -> None:
    """
    When pad_groups is False, groups are separated by single newlines.
    """
    content = """
```python group="test"
x = 1
```

Text here.

More text.

```python group="test"
y = 2
```
"""
    test_document = tmp_path / "test.mdx"
    test_document.write_text(data=content, encoding="utf-8")

    evaluator = BlockAccumulatorEvaluator(namespace_key="blocks")
    code_block_parser = CodeBlockParser(language="python")
    group_parser = AttributeGroupedSourceParser(
        code_block_parser=code_block_parser,
        evaluator=evaluator,
        attribute_name="group",
        pad_groups=False,
    )

    sybil = Sybil(parsers=[group_parser])
    document = sybil.parse(path=test_document)

    for example in document.examples():
        example.evaluate()

    assert len(document.namespace["blocks"]) == 1
    # With pad_groups=False, should have minimal padding (single newline)
    expected = "x = 1\n\ny = 2\n"
    assert document.namespace["blocks"][0] == expected


def test_attribute_group_empty_group(tmp_path: Path) -> None:
    """
    Empty groups (no code blocks) don't cause errors.
    """
    content = """
```python
x = 1
```
"""
    test_document = tmp_path / "test.mdx"
    test_document.write_text(data=content, encoding="utf-8")

    evaluator = BlockAccumulatorEvaluator(namespace_key="blocks")
    code_block_parser = CodeBlockParser(language="python")
    group_parser = AttributeGroupedSourceParser(
        code_block_parser=code_block_parser,
        evaluator=evaluator,
        attribute_name="group",
        pad_groups=True,
    )

    sybil = Sybil(parsers=[group_parser])
    document = sybil.parse(path=test_document)

    # No examples should be created since no blocks have the group attribute
    examples = list(document.examples())
    assert len(examples) == 0

    # No grouped blocks, since no blocks have the group attribute
    assert document.namespace.get("blocks", []) == []
