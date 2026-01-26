"""
Attribute-based grouped source parser tests for MDX.
"""

import textwrap
from pathlib import Path

from sybil import Sybil

from sybil_extras.evaluators.block_accumulator import BlockAccumulatorEvaluator
from sybil_extras.evaluators.no_op import NoOpEvaluator
from sybil_extras.parsers.mdx.attribute_grouped_source import (
    AttributeGroupedSourceParser,
)
from sybil_extras.parsers.mdx.codeblock import CodeBlockParser


def test_attribute_group_single_group(tmp_path: Path) -> None:
    """
    The attribute group parser groups examples with the same group attribute.
    """
    content = textwrap.dedent(
        text="""
        ```python group="example1"
        from pprint import pp
        ```

        Some text in between.

        ```python group="example1"
        pp({"hello": "world"})
        ```
        """,
    )
    test_document = tmp_path / "test.mdx"
    test_document.write_text(data=content, encoding="utf-8")

    evaluator = BlockAccumulatorEvaluator(namespace_key="blocks")
    code_block_parser = CodeBlockParser(language="python")
    group_parser = AttributeGroupedSourceParser(
        code_block_parser=code_block_parser,
        evaluator=evaluator,
        attribute_name="group",
        pad_groups=True,
        ungrouped_evaluator=NoOpEvaluator(),
    )

    sybil = Sybil(parsers=[group_parser])
    document = sybil.parse(path=test_document)

    for example in document.examples():
        example.evaluate()

    expected = 'from pprint import pp\n\n\n\n\n\npp({"hello": "world"})\n'
    assert document.namespace["blocks"] == [expected]


def test_attribute_group_multiple_groups(tmp_path: Path) -> None:
    """Multiple groups are handled separately and in document order.

    Groups should not interleave to avoid region overlap issues.
    """
    content = textwrap.dedent(
        text="""
        ```python group="setup"
        x = []
        ```

        ```python group="setup"
        x = [*x, 1]
        ```

        ```python group="setup"
        x = [*x, 2]
        ```

        ```python group="example"
        y = []
        ```

        ```python group="example"
        y = [*y, 10]
        ```
        """,
    )
    test_document = tmp_path / "test.mdx"
    test_document.write_text(data=content, encoding="utf-8")

    evaluator = BlockAccumulatorEvaluator(namespace_key="blocks")
    code_block_parser = CodeBlockParser(language="python")
    group_parser = AttributeGroupedSourceParser(
        code_block_parser=code_block_parser,
        evaluator=evaluator,
        attribute_name="group",
        pad_groups=True,
        ungrouped_evaluator=NoOpEvaluator(),
    )

    sybil = Sybil(parsers=[group_parser])
    document = sybil.parse(path=test_document)

    for example in document.examples():
        example.evaluate()

    expected_setup = "x = []\n\n\n\nx = [*x, 1]\n\n\n\nx = [*x, 2]\n"
    expected_example = "y = []\n\n\n\ny = [*y, 10]\n"
    assert document.namespace["blocks"] == [expected_setup, expected_example]


def test_attribute_group_no_group_attribute(tmp_path: Path) -> None:
    """
    Code blocks without the group attribute are not grouped.
    """
    content = textwrap.dedent(
        text="""
        ```python
        x = 1
        ```

        ```python group="example"
        y = 2
        ```

        ```python
        z = 3
        ```
        """,
    )
    test_document = tmp_path / "test.mdx"
    test_document.write_text(data=content, encoding="utf-8")

    evaluator = BlockAccumulatorEvaluator(namespace_key="blocks")
    code_block_parser = CodeBlockParser(language="python")
    group_parser = AttributeGroupedSourceParser(
        code_block_parser=code_block_parser,
        evaluator=evaluator,
        attribute_name="group",
        pad_groups=True,
        ungrouped_evaluator=NoOpEvaluator(),
    )

    sybil = Sybil(parsers=[group_parser])
    document = sybil.parse(path=test_document)

    for example in document.examples():
        example.evaluate()

    assert document.namespace["blocks"] == ["y = 2\n"]


def test_attribute_group_custom_attribute_name(tmp_path: Path) -> None:
    """
    Custom attribute names can be used for grouping.
    """
    content = textwrap.dedent(
        text="""
        ```python mygroup="test1"
        a = 1
        ```

        ```python mygroup="test1"
        b = 2
        ```
        """,
    )
    test_document = tmp_path / "test.mdx"
    test_document.write_text(data=content, encoding="utf-8")

    evaluator = BlockAccumulatorEvaluator(namespace_key="blocks")
    code_block_parser = CodeBlockParser(language="python")
    group_parser = AttributeGroupedSourceParser(
        code_block_parser=code_block_parser,
        evaluator=evaluator,
        attribute_name="mygroup",
        pad_groups=True,
        ungrouped_evaluator=NoOpEvaluator(),
    )

    sybil = Sybil(parsers=[group_parser])
    document = sybil.parse(path=test_document)

    for example in document.examples():
        example.evaluate()

    expected = "a = 1\n\n\n\nb = 2\n"
    assert document.namespace["blocks"] == [expected]


def test_attribute_group_with_other_attributes(tmp_path: Path) -> None:
    """
    Code blocks with multiple attributes still group correctly.
    """
    content = textwrap.dedent(
        text="""
        ```python title="example.py" group="setup" showLineNumbers
        value = 7
        ```

        ```python group="setup" title="example2.py"
        result = value * 2
        ```
        """,
    )
    test_document = tmp_path / "test.mdx"
    test_document.write_text(data=content, encoding="utf-8")

    evaluator = BlockAccumulatorEvaluator(namespace_key="blocks")
    code_block_parser = CodeBlockParser(language="python")
    group_parser = AttributeGroupedSourceParser(
        code_block_parser=code_block_parser,
        evaluator=evaluator,
        attribute_name="group",
        pad_groups=True,
        ungrouped_evaluator=NoOpEvaluator(),
    )

    sybil = Sybil(parsers=[group_parser])
    document = sybil.parse(path=test_document)

    for example in document.examples():
        example.evaluate()

    expected = "value = 7\n\n\n\nresult = value * 2\n"
    assert document.namespace["blocks"] == [expected]


def test_attribute_group_pad_groups_false(tmp_path: Path) -> None:
    """
    When pad_groups is False, groups are separated by single newlines.
    """
    content = textwrap.dedent(
        text="""
        ```python group="test"
        x = 1
        ```

        Text here.

        More text.

        ```python group="test"
        y = 2
        ```
        """,
    )
    test_document = tmp_path / "test.mdx"
    test_document.write_text(data=content, encoding="utf-8")

    evaluator = BlockAccumulatorEvaluator(namespace_key="blocks")
    code_block_parser = CodeBlockParser(language="python")
    group_parser = AttributeGroupedSourceParser(
        code_block_parser=code_block_parser,
        evaluator=evaluator,
        attribute_name="group",
        pad_groups=False,
        ungrouped_evaluator=NoOpEvaluator(),
    )

    sybil = Sybil(parsers=[group_parser])
    document = sybil.parse(path=test_document)

    for example in document.examples():
        example.evaluate()

    expected = "x = 1\n\ny = 2\n"
    assert document.namespace["blocks"] == [expected]


def test_attribute_group_interleaved_groups(tmp_path: Path) -> None:
    """
    Groups can interleave.
    """
    content = textwrap.dedent(
        text="""
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
        """,
    )
    test_document = tmp_path / "test.mdx"
    test_document.write_text(data=content, encoding="utf-8")

    evaluator = BlockAccumulatorEvaluator(namespace_key="blocks")
    code_block_parser = CodeBlockParser(language="python")
    group_parser = AttributeGroupedSourceParser(
        code_block_parser=code_block_parser,
        evaluator=evaluator,
        attribute_name="group",
        pad_groups=False,
        ungrouped_evaluator=NoOpEvaluator(),
    )

    sybil = Sybil(parsers=[group_parser])

    document = sybil.parse(path=test_document)

    for example in document.examples():
        example.evaluate()

    expected_setup = "x = []\n\nx = [*x, 1]\n\nx = [*x, 2]\n"
    expected_example = "y = []\n\ny = [*y, 10]\n"
    assert document.namespace["blocks"] == [expected_setup, expected_example]


def test_attribute_group_ungrouped_evaluator(tmp_path: Path) -> None:
    """
    Code blocks without the group attribute use the ungrouped_evaluator.
    """
    content = textwrap.dedent(
        text="""
        ```python
        x = 1
        ```

        ```python group="example"
        y = 2
        ```

        ```python group="example"
        z = 3
        ```

        ```python
        w = 4
        ```
        """,
    )
    test_document = tmp_path / "test.mdx"
    test_document.write_text(data=content, encoding="utf-8")

    grouped_evaluator = BlockAccumulatorEvaluator(namespace_key="grouped")
    ungrouped_evaluator = BlockAccumulatorEvaluator(namespace_key="ungrouped")
    code_block_parser = CodeBlockParser(language="python")
    group_parser = AttributeGroupedSourceParser(
        code_block_parser=code_block_parser,
        evaluator=grouped_evaluator,
        attribute_name="group",
        pad_groups=False,
        ungrouped_evaluator=ungrouped_evaluator,
    )

    sybil = Sybil(parsers=[group_parser])
    document = sybil.parse(path=test_document)

    for example in document.examples():
        example.evaluate()

    # Grouped blocks should be combined
    assert document.namespace["grouped"] == ["y = 2\n\nz = 3\n"]
    # Ungrouped blocks should be evaluated individually
    assert document.namespace["ungrouped"] == ["x = 1\n", "w = 4\n"]
