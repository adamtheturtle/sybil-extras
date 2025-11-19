"""
Tests for the group all parser for MyST.
"""

from pathlib import Path

from sybil import Sybil
from sybil.example import Example
from sybil.parsers.myst.codeblock import CodeBlockParser
from sybil.parsers.myst.skip import SkipParser

from sybil_extras.evaluators.no_op import NoOpEvaluator
from sybil_extras.parsers.myst.group_all import GroupAllParser


def test_group_all(tmp_path: Path) -> None:
    """
    The group all parser groups all examples in a document.
    """
    content = """\

```python
x = []
```

```python
x = [*x, 1]
```

```python
x = [*x, 2]
```
"""

    test_document = tmp_path / "test.md"
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

    group_all_parser = GroupAllParser(
        evaluator=evaluator,
        pad_groups=True,
    )
    code_block_parser = CodeBlockParser(language="python", evaluator=evaluator)

    sybil = Sybil(parsers=[code_block_parser, group_all_parser])
    document = sybil.parse(path=test_document)

    for example in document.examples():
        example.evaluate()

    assert document.namespace["blocks"] == [
        "x = []\n\n\n\nx = [*x, 1]\n\n\n\nx = [*x, 2]\n",
    ]
    assert len(document.evaluators) == 0


def test_group_all_single_block(tmp_path: Path) -> None:
    """
    The group all parser works with a single code block.
    """
    content = """\

```python
x = []
```
"""

    test_document = tmp_path / "test.md"
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

    group_all_parser = GroupAllParser(
        evaluator=evaluator,
        pad_groups=True,
    )
    code_block_parser = CodeBlockParser(language="python", evaluator=evaluator)

    sybil = Sybil(parsers=[code_block_parser, group_all_parser])
    document = sybil.parse(path=test_document)

    for example in document.examples():
        example.evaluate()

    assert document.namespace["blocks"] == [
        "x = []\n",
    ]


def test_group_all_empty_document(tmp_path: Path) -> None:
    """
    The group all parser handles an empty document gracefully.
    """
    content = """\
# Empty document

No code blocks here.
"""

    test_document = tmp_path / "test.md"
    test_document.write_text(data=content, encoding="utf-8")

    group_all_parser = GroupAllParser(
        evaluator=NoOpEvaluator(),
        pad_groups=True,
    )
    code_block_parser = CodeBlockParser(language="python")

    sybil = Sybil(parsers=[code_block_parser, group_all_parser])
    document = sybil.parse(path=test_document)

    examples = list(document.examples())
    assert len(examples) == 1

    # Evaluate all examples (should not raise)
    for example in examples:
        example.evaluate()


def test_group_all_no_pad(tmp_path: Path) -> None:
    """
    The group all parser can avoid padding groups.
    """
    content = """\

```python
x = []
```

```python
x = [*x, 1]
```

```python
x = [*x, 2]
```
"""

    test_document = tmp_path / "test.md"
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

    group_all_parser = GroupAllParser(
        evaluator=evaluator,
        pad_groups=False,
    )
    code_block_parser = CodeBlockParser(language="python", evaluator=evaluator)

    sybil = Sybil(parsers=[code_block_parser, group_all_parser])
    document = sybil.parse(path=test_document)

    for example in document.examples():
        example.evaluate()

    # Should have one combined block with only one newline between blocks
    assert document.namespace["blocks"] == [
        "x = []\n\nx = [*x, 1]\n\nx = [*x, 2]\n",
    ]


def test_group_all_with_skip(tmp_path: Path) -> None:
    """The group all parser works with skip directives.

    Skip directives create examples without source, which should be
    handled by raising NotEvaluated.
    """
    content = """\

```python
x = []
```

<!--- skip: next -->

```python
x = [*x, 1]
```

```python
x = [*x, 2]
```
"""

    test_document = tmp_path / "test.md"
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

    group_all_parser = GroupAllParser(
        evaluator=evaluator,
        pad_groups=True,
    )
    code_block_parser = CodeBlockParser(language="python", evaluator=evaluator)
    skip_parser = SkipParser()

    sybil = Sybil(parsers=[code_block_parser, skip_parser, group_all_parser])
    document = sybil.parse(path=test_document)

    for example in document.examples():
        example.evaluate()

    # The skip directive should cause the second block to be skipped
    # but still group the first and third blocks
    # Note: padding preserves line numbers, so the skipped lines are included
    assert document.namespace["blocks"] == [
        "x = []\n\n\n\n\n\n\n\n\n\nx = [*x, 2]\n",
    ]
