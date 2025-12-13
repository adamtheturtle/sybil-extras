"""
Abstract parser that groups all code blocks in a document.
"""

import threading
from collections.abc import Iterable

from beartype import beartype
from sybil import Document, Example, Region
from sybil.example import NotEvaluated
from sybil.typing import Evaluator

from ._grouping_utils import (
    count_expected_code_blocks,
    create_combined_example,
    create_combined_region,
    has_source,
)


@beartype
class _GroupAllState:
    """
    State for grouping all examples in a document.
    """

    def __init__(self, *, expected_code_blocks: int) -> None:
        """
        Initialize the group all state.
        """
        self.expected_code_blocks = expected_code_blocks
        self.examples: list[Example] = []
        self.lock = threading.Lock()
        self.ready = threading.Condition(lock=self.lock)
        self.collected_count = 0


@beartype
class _GroupAllEvaluator:
    """
    Evaluator that collects all examples and evaluates them as one.
    """

    def __init__(
        self,
        *,
        evaluator: Evaluator,
        pad_groups: bool,
    ) -> None:
        """
        Args:
            evaluator: The evaluator to use for evaluating the combined region.
            pad_groups: Whether to pad groups with empty lines.
                This is useful for error messages that reference line numbers.
                However, this is detrimental to commands that expect the file
                to not have a bunch of newlines in it, such as formatters.
        """
        self._document_state: dict[Document, _GroupAllState] = {}
        self._evaluator = evaluator
        self._pad_groups = pad_groups

    def register_document(
        self,
        document: Document,
        expected_code_blocks: int,
    ) -> None:
        """Register a document for grouping.

        Called at parse time, not evaluation time.
        """
        self._document_state[document] = _GroupAllState(
            expected_code_blocks=expected_code_blocks,
        )

    def collect(self, example: Example) -> None:
        """
        Collect an example to be grouped.
        """
        state = self._document_state[example.document]

        with state.ready:
            if has_source(example=example):
                state.examples.append(example)
                state.collected_count += 1
                state.ready.notify_all()
                return

        raise NotEvaluated

    def finalize(self, example: Example) -> None:
        """
        Finalize the grouping and evaluate all collected examples.
        """
        state = self._document_state[example.document]

        with state.ready:
            # Wait until all expected code blocks have been collected
            while state.collected_count < state.expected_code_blocks:
                state.ready.wait()

            if not state.examples:
                # No examples to group, do nothing
                example.document.pop_evaluator(evaluator=self)
                del self._document_state[example.document]
                return

            # Sort examples by their position in the document to ensure
            # correct order regardless of evaluation order (thread-safety)
            sorted_examples = sorted(
                state.examples,
                key=lambda ex: ex.region.start,
            )
            try:
                region = create_combined_region(
                    examples=sorted_examples,
                    evaluator=self._evaluator,
                    pad_groups=self._pad_groups,
                )
                new_example = create_combined_example(
                    examples=sorted_examples,
                    region=region,
                )
                self._evaluator(new_example)
            finally:
                example.document.pop_evaluator(evaluator=self)
                # Clean up document state to prevent memory leaks when reusing
                # parser instances across multiple documents.
                del self._document_state[example.document]

    def __call__(self, example: Example) -> None:
        """
        Call the evaluator.
        """
        # We use ``id`` equivalence rather than ``is`` to avoid a
        # ``pyright`` error:
        # https://github.com/microsoft/pyright/issues/9932
        if id(example.region.evaluator) == id(self):
            self.finalize(example=example)
            return

        self.collect(example=example)

    # Satisfy vulture.
    _caller = __call__


@beartype
class AbstractGroupAllParser:
    """
    An abstract parser that groups all code blocks in a document without
    markup.
    """

    def __init__(
        self,
        *,
        evaluator: Evaluator,
        pad_groups: bool,
    ) -> None:
        """
        Args:
            evaluator: The evaluator to use for evaluating the combined region.
            pad_groups: Whether to pad groups with empty lines.
                This is useful for error messages that reference line numbers.
                However, this is detrimental to commands that expect the file
                to not have a bunch of newlines in it, such as formatters.
        """
        self._evaluator = _GroupAllEvaluator(
            evaluator=evaluator,
            pad_groups=pad_groups,
        )

    def __call__(self, document: Document) -> Iterable[Region]:
        """
        Yield a single region at the end of the document to trigger
        finalization.
        """
        # Count code blocks by examining existing examples.
        # At parse time, previous parsers have already added their regions.
        expected_code_blocks = count_expected_code_blocks(
            examples=document.examples(),
        )

        # Register the document at parse time
        self._evaluator.register_document(
            document=document,
            expected_code_blocks=expected_code_blocks,
        )

        # Push the evaluator at the start of the document
        document.push_evaluator(evaluator=self._evaluator)

        # Create a marker at the end of the document to trigger finalization
        yield Region(
            start=len(document.text),
            end=len(document.text),
            parsed="",
            evaluator=self._evaluator,
        )
