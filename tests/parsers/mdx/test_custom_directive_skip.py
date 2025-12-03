"""
Tests for the MDX custom directive skip parser.
"""

from pathlib import Path

from sybil import Sybil
from sybil.example import Example

from sybil_extras.parsers.mdx.codeblock import CodeBlockParser
from sybil_extras.parsers.mdx.custom_directive_skip import (
    CustomDirectiveSkipParser,
)


def test_skip_basic(tmp_path: Path) -> None:
    """
    Test basic skip functionality.
    """
    content = """\
```python
x = []
```

<!-- myskip: next -->

```python
x = [*x, 2]
```

```python
x = [*x, 3]
```
"""
    test_document = tmp_path / "test.mdx"
    test_document.write_text(data=content, encoding="utf-8")

    skip_parser = CustomDirectiveSkipParser(directive="myskip")

    def evaluator(example: Example) -> None:
        """
        Execute the code in the document namespace.
        """
        exec(example.parsed, example.document.namespace)  # noqa: S102

    code_block_parser = CodeBlockParser(language="python", evaluator=evaluator)

    sybil = Sybil(parsers=[skip_parser, code_block_parser])
    document = sybil.parse(path=test_document)

    for example in document.examples():
        example.evaluate()

    # The second block should be skipped, so x should be [3] not [2, 3]
    assert document.namespace["x"] == [3]


def test_skip_start_end(tmp_path: Path) -> None:
    """
    Test skip with start and end directives.
    """
    content = """\
```python
x = []
```

<!-- myskip: start -->

```python
x = [*x, 2]
```

```python
x = [*x, 3]
```

<!-- myskip: end -->

```python
x = [*x, 4]
```
"""
    test_document = tmp_path / "test.mdx"
    test_document.write_text(data=content, encoding="utf-8")

    skip_parser = CustomDirectiveSkipParser(directive="myskip")

    def evaluator(example: Example) -> None:
        """
        Execute the code in the document namespace.
        """
        exec(example.parsed, example.document.namespace)  # noqa: S102

    code_block_parser = CodeBlockParser(language="python", evaluator=evaluator)

    sybil = Sybil(parsers=[skip_parser, code_block_parser])
    document = sybil.parse(path=test_document)

    for example in document.examples():
        example.evaluate()

    # The second and third blocks should be skipped, so x should be [4]
    assert document.namespace["x"] == [4]


def test_skip_with_custom_directive_name(tmp_path: Path) -> None:
    """
    Test that custom directive names work correctly.
    """
    content = """\
```python
x = []
```

<!-- ignore: next -->

```python
x = [*x, 2]
```
"""
    test_document = tmp_path / "test.mdx"
    test_document.write_text(data=content, encoding="utf-8")

    skip_parser = CustomDirectiveSkipParser(directive="ignore")

    def evaluator(example: Example) -> None:
        """
        Execute the code in the document namespace.
        """
        exec(example.parsed, example.document.namespace)  # noqa: S102

    code_block_parser = CodeBlockParser(language="python", evaluator=evaluator)

    sybil = Sybil(parsers=[skip_parser, code_block_parser])
    document = sybil.parse(path=test_document)

    for example in document.examples():
        example.evaluate()

    # The second block should be skipped
    assert document.namespace["x"] == []


def test_no_skip_when_directive_absent(tmp_path: Path) -> None:
    """
    Test that blocks are not skipped when no skip directive is present.
    """
    content = """\
```python
x = []
```

```python
x = [*x, 2]
```

```python
x = [*x, 3]
```
"""
    test_document = tmp_path / "test.mdx"
    test_document.write_text(data=content, encoding="utf-8")

    skip_parser = CustomDirectiveSkipParser(directive="myskip")

    def evaluator(example: Example) -> None:
        """
        Execute the code in the document namespace.
        """
        exec(example.parsed, example.document.namespace)  # noqa: S102

    code_block_parser = CodeBlockParser(language="python", evaluator=evaluator)

    sybil = Sybil(parsers=[skip_parser, code_block_parser])
    document = sybil.parse(path=test_document)

    for example in document.examples():
        example.evaluate()

    # All blocks should execute
    assert document.namespace["x"] == [2, 3]


def test_skip_with_attributes(tmp_path: Path) -> None:
    """
    Test skip functionality with MDX code blocks that have attributes.
    """
    content = """\
```python title="first.py"
x = []
```

<!-- myskip: next -->

```python title="second.py"
x = [*x, 2]
```

```python title="third.py"
x = [*x, 3]
```
"""
    test_document = tmp_path / "test.mdx"
    test_document.write_text(data=content, encoding="utf-8")

    skip_parser = CustomDirectiveSkipParser(directive="myskip")

    def evaluator(example: Example) -> None:
        """
        Execute the code in the document namespace.
        """
        exec(example.parsed, example.document.namespace)  # noqa: S102

    code_block_parser = CodeBlockParser(language="python", evaluator=evaluator)

    sybil = Sybil(parsers=[skip_parser, code_block_parser])
    document = sybil.parse(path=test_document)

    for example in document.examples():
        example.evaluate()

    # The second block should be skipped
    assert document.namespace["x"] == [3]


def test_skipper_property() -> None:
    """
    Test that the skipper property is accessible.
    """
    skip_parser = CustomDirectiveSkipParser(directive="myskip")

    assert skip_parser.skipper is not None
    assert skip_parser.skipper.directive == "myskip"
