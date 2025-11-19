"""
Abstract parser that groups all code blocks in a document.
"""

from collections import defaultdict
from collections.abc import Iterable

from sybil import Document, Example, Region
from sybil.example import NotEvaluated
from sybil.typing import Evaluator

from ._grouping_utils import (
    create_combined_example,
    create_combined_region,
    has_source,
)


class _GroupAllState:
    """
    State for grouping all examples in a document.
    """

    def __init__(self) -> None:
        """
        Initialize the group all state.
        """
        self.examples: list[Example] = []


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
        self._document_state: dict[Document, _GroupAllState] = defaultdict(
            _GroupAllState
        )
        self._evaluator = evaluator
        self._pad_groups = pad_groups

    def collect(self, example: Example) -> None:
        """
        Collect an example to be grouped.
        """
        state = self._document_state[example.document]
        if has_source(example=example):
            state.examples.append(example)
            return

        raise NotEvaluated

    def finalize(self, example: Example) -> None:
        """
        Finalize the grouping and evaluate all collected examples.
        """
        state = self._document_state[example.document]

        if not state.examples:
            # No examples to group, do nothing
            example.document.pop_evaluator(evaluator=self)
            del self._document_state[example.document]
            return

        region = create_combined_region(
            examples=state.examples,
            evaluator=self._evaluator,
            pad_groups=self._pad_groups,
        )
        new_example = create_combined_example(
            examples=state.examples,
            region=region,
        )
        self._evaluator(new_example)

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
        # Push the evaluator at the start of the document
        document.push_evaluator(evaluator=self._evaluator)

        # Create a marker at the end of the document to trigger finalization
        yield Region(
            start=len(document.text),
            end=len(document.text),
            parsed="",
            evaluator=self._evaluator,
        )
