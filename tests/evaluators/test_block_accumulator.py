"""Tests for the BlockAccumulatorEvaluator."""

import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from sybil import Example, Sybil
from sybil.parsers.rest.codeblock import CodeBlockParser

from sybil_extras.evaluators.block_accumulator import BlockAccumulatorEvaluator


class _ConcurrencyTrackingNamespace(dict[str, object]):
    """A namespace that records the peak overlap of concurrent reads."""

    def __init__(self) -> None:
        """Initialize the namespace."""
        super().__init__()
        self._active = 0
        self.max_concurrent = 0
        self._lock = threading.Lock()

    def get(self, key: object, default: object = None) -> object:
        """Get a value while recording how many reads overlap."""
        with self._lock:
            self._active += 1
            self.max_concurrent = max(self.max_concurrent, self._active)
        try:
            time.sleep(0.05)
            # ``key`` is typed ``object`` to match ``dict.get`` across type
            # checkers; the namespace is only ever queried with string keys.
            assert isinstance(key, str)
            return super().get(key, default)
        finally:
            with self._lock:
                self._active -= 1


def test_concurrent_evaluation_retains_all_blocks(tmp_path: Path) -> None:
    """Concurrent evaluations serialize namespace updates."""
    content = """\
.. code-block:: python

   first

.. code-block:: python

   second
"""
    test_document = tmp_path / "test.rst"
    test_document.write_text(data=content, encoding="utf-8")
    evaluator = BlockAccumulatorEvaluator(namespace_key="blocks")
    parser = CodeBlockParser(language="python", evaluator=evaluator)
    document = Sybil(parsers=[parser]).parse(path=test_document)
    namespace = _ConcurrencyTrackingNamespace()
    document.namespace = namespace
    examples = list(document.examples())
    start = threading.Barrier(parties=2)

    def evaluate(example: Example) -> None:
        """Evaluate an example after both workers are ready."""
        start.wait()
        example.evaluate()

    with ThreadPoolExecutor(max_workers=2) as executor:
        list(executor.map(evaluate, examples))

    assert namespace.max_concurrent == 1
    blocks_object: object = document.namespace["blocks"]
    assert blocks_object in (
        ["first\n", "second"],
        ["second", "first\n"],
    )


def test_accumulates_blocks(tmp_path: Path) -> None:
    """The evaluator accumulates parsed code blocks in the namespace."""
    content = """\
.. code-block:: python

   x = 1

.. code-block:: python

   y = 2

.. code-block:: python

   z = 3
"""
    test_document = tmp_path / "test.rst"
    test_document.write_text(data=content, encoding="utf-8")

    evaluator = BlockAccumulatorEvaluator(namespace_key="blocks")
    parser = CodeBlockParser(language="python", evaluator=evaluator)
    sybil = Sybil(parsers=[parser])
    document = sybil.parse(path=test_document)

    for example in document.examples():
        example.evaluate()

    assert document.namespace["blocks"] == ["x = 1\n", "y = 2\n", "z = 3"]


def test_custom_namespace_key(tmp_path: Path) -> None:
    """The evaluator can use a custom namespace key."""
    content = """\
.. code-block:: python

   x = 1

.. code-block:: python

   y = 2
"""
    test_document = tmp_path / "test.rst"
    test_document.write_text(data=content, encoding="utf-8")

    evaluator = BlockAccumulatorEvaluator(namespace_key="custom_key")
    parser = CodeBlockParser(language="python", evaluator=evaluator)
    sybil = Sybil(parsers=[parser])
    document = sybil.parse(path=test_document)

    for example in document.examples():
        example.evaluate()

    assert document.namespace["custom_key"] == ["x = 1\n", "y = 2"]
    assert "blocks" not in document.namespace


def test_single_block(tmp_path: Path) -> None:
    """The evaluator handles a single code block."""
    content = """\
.. code-block:: python

   x = 1
"""
    test_document = tmp_path / "test.rst"
    test_document.write_text(data=content, encoding="utf-8")

    evaluator = BlockAccumulatorEvaluator(namespace_key="blocks")
    parser = CodeBlockParser(language="python", evaluator=evaluator)
    sybil = Sybil(parsers=[parser])
    document = sybil.parse(path=test_document)

    for example in document.examples():
        example.evaluate()

    assert document.namespace["blocks"] == ["x = 1"]


def test_preserves_content(tmp_path: Path) -> None:
    """The evaluator preserves the exact content of code blocks."""
    content = """\
.. code-block:: python

   # Comment with special chars: !@#$%^&*()
   x = "string with 'quotes'"
   y = '''triple
   quoted
   string'''
"""
    test_document = tmp_path / "test.rst"
    test_document.write_text(data=content, encoding="utf-8")

    evaluator = BlockAccumulatorEvaluator(namespace_key="blocks")
    parser = CodeBlockParser(language="python", evaluator=evaluator)
    sybil = Sybil(parsers=[parser])
    document = sybil.parse(path=test_document)

    for example in document.examples():
        example.evaluate()

    expected_content = """\
# Comment with special chars: !@#$%^&*()
x = "string with 'quotes'"
y = '''triple
quoted
string'''"""
    assert document.namespace["blocks"] == [expected_content]
