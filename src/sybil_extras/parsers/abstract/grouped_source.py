"""
An abstract parser for grouping blocks of source code.
"""

import threading
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from typing import Literal

from beartype import beartype
from sybil import Document, Example, Region
from sybil.example import NotEvaluated
from sybil.parsers.abstract.lexers import LexerCollection
from sybil.typing import Evaluator, Lexer

from ._grouping_utils import (
    create_combined_example,
    create_combined_region,
    has_source,
)


@beartype
@dataclass
class _GroupMarker:
    """
    A marker for a group start or end.
    """

    action: Literal["start", "end"]
    group_id: int
    # Store the boundaries so code blocks can determine membership
    start_pos: int
    end_pos: int


@beartype
class _GroupState:
    """
    State for a single group.
    """

    def __init__(self, *, start_pos: int, end_pos: int) -> None:
        """
        Initialize the group state.
        """
        self.start_pos = start_pos
        self.end_pos = end_pos
        self.examples: list[Example] = []
        self.lock = threading.Lock()


@beartype
class _Grouper:
    """
    Group blocks of source code.
    """

    def __init__(
        self,
        *,
        evaluator: Evaluator,
        directive: str,
        pad_groups: bool,
    ) -> None:
        """
        Args:
            evaluator: The evaluator to use for evaluating the combined region.
            directive: The name of the directive to use for grouping.
            pad_groups: Whether to pad groups with empty lines.
                This is useful for error messages that reference line numbers.
                However, this is detrimental to commands that expect the file
                to not have a bunch of newlines in it, such as formatters.
        """
        # State is keyed by (document, group_id) to allow multiple groups
        # in the same document to be processed in parallel.
        self._group_state: dict[tuple[Document, int], _GroupState] = {}
        self._group_state_lock = threading.Lock()
        self._evaluator = evaluator
        self._directive = directive
        self._pad_groups = pad_groups
        # Track group boundaries per document for determining membership
        # Maps document -> list of (group_id, start_pos, end_pos)
        self._group_boundaries: dict[Document, list[tuple[int, int, int]]] = {}
        self._group_boundaries_lock = threading.Lock()

    def register_group(
        self,
        document: Document,
        group_id: int,
        start_pos: int,
        end_pos: int,
    ) -> None:
        """Register a group's boundaries for later membership lookup.

        Called at parse time, not evaluation time.
        """
        with self._group_boundaries_lock:
            if document not in self._group_boundaries:
                self._group_boundaries[document] = []
            self._group_boundaries[document].append(
                (group_id, start_pos, end_pos)
            )
        # Pre-create the group state
        key = (document, group_id)
        with self._group_state_lock:
            if key not in self._group_state:
                self._group_state[key] = _GroupState(
                    start_pos=start_pos,
                    end_pos=end_pos,
                )

    def _find_containing_group(
        self,
        document: Document,
        position: int,
    ) -> int | None:
        """
        Find which group contains the given position, if any.
        """
        with self._group_boundaries_lock:
            boundaries = self._group_boundaries.get(document, [])
            for group_id, start_pos, end_pos in boundaries:
                if start_pos < position < end_pos:
                    return group_id
        return None

    def _get_group_state(
        self,
        document: Document,
        group_id: int,
    ) -> _GroupState:
        """
        Get the state for a specific group.
        """
        key = (document, group_id)
        with self._group_state_lock:
            return self._group_state[key]

    def _cleanup_group_state(
        self,
        document: Document,
        group_id: int,
    ) -> None:
        """
        Clean up the state for a specific group.
        """
        key = (document, group_id)
        with self._group_state_lock:
            if key in self._group_state:
                del self._group_state[key]
        with self._group_boundaries_lock:
            if document in self._group_boundaries:
                self._group_boundaries[document] = [
                    b
                    for b in self._group_boundaries[document]
                    if b[0] != group_id
                ]
                if not self._group_boundaries[document]:
                    del self._group_boundaries[document]

    def _cleanup_document(self, document: Document) -> None:
        """Clean up all state for a document.

        Called when the last group in the document is finalized.
        """
        with self._group_boundaries_lock:
            remaining = self._group_boundaries.get(document, [])
            if not remaining:
                document.pop_evaluator(evaluator=self)

    def _evaluate_grouper_example(self, example: Example) -> None:
        """
        Evaluate a grouper marker.
        """
        marker: _GroupMarker = example.parsed
        state = self._get_group_state(example.document, marker.group_id)

        with state.lock:
            if marker.action == "start":
                return

            try:
                if state.examples:
                    # Sort examples by their position in the document to ensure
                    # correct order regardless of evaluation order
                    # (for thread-safety).
                    sorted_examples = sorted(
                        state.examples,
                        key=lambda ex: ex.region.start,
                    )
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
                self._cleanup_group_state(example.document, marker.group_id)
                self._cleanup_document(example.document)

    def _evaluate_other_example(self, example: Example) -> None:
        """Evaluate an example that is not a group example.

        Determine group membership based on position.
        """
        # Find which group contains this example based on position
        group_id = self._find_containing_group(
            example.document,
            example.region.start,
        )

        if group_id is None:
            raise NotEvaluated

        state = self._get_group_state(example.document, group_id)

        with state.lock:
            if has_source(example=example):
                state.examples.append(example)
                return

        raise NotEvaluated

    def __call__(self, /, example: Example) -> None:
        """
        Call the evaluator.
        """
        # We use ``id`` equivalence rather than ``is`` to avoid a
        # ``pyright`` error:
        # https://github.com/microsoft/pyright/issues/9932
        if id(example.region.evaluator) == id(self):
            self._evaluate_grouper_example(example=example)
            return

        self._evaluate_other_example(example=example)

    # Satisfy vulture.
    _caller = __call__


@beartype
class AbstractGroupedSourceParser:
    """
    An abstract parser for grouping blocks of source code.
    """

    def __init__(
        self,
        *,
        lexers: Sequence[Lexer],
        evaluator: Evaluator,
        directive: str,
        pad_groups: bool,
    ) -> None:
        """
        Args:
            lexers: The lexers to use to find regions.
            evaluator: The evaluator to use for evaluating the combined region.
            directive: The name of the directive to use for grouping.
            pad_groups: Whether to pad groups with empty lines.
                This is useful for error messages that reference line numbers.
                However, this is detrimental to commands that expect the file
                to not have a bunch of newlines in it, such as formatters.
        """
        self._lexers: LexerCollection = LexerCollection(lexers)
        self._grouper: _Grouper = _Grouper(
            evaluator=evaluator,
            directive=directive,
            pad_groups=pad_groups,
        )
        self._directive = directive

    def __call__(self, document: Document) -> Iterable[Region]:
        """
        Yield regions to evaluate, grouped by start and end comments.
        """
        # First pass: collect all start/end markers
        markers: list[tuple[int, int, str]] = []  # (start, end, action)
        for lexed in self._lexers(document):
            arguments = lexed.lexemes["arguments"]
            if not arguments:
                directive = lexed.lexemes["directive"]
                msg = f"missing arguments to {directive}"
                raise ValueError(msg)

            if arguments not in ("start", "end"):
                directive = lexed.lexemes["directive"]
                msg = f"malformed arguments to {directive}: {arguments!r}"
                raise ValueError(msg)

            markers.append((lexed.start, lexed.end, arguments))

        if not markers:
            return

        # Validate and pair up start/end markers, register groups
        regions: list[Region] = []
        group_id = 0
        i = 0
        while i < len(markers):
            start_start, start_end, start_action = markers[i]
            if start_action != "start":
                msg = (
                    f"'{self._directive}: {start_action}' "
                    f"must follow '{self._directive}: start'"
                )
                raise ValueError(msg)

            if i + 1 >= len(markers):
                msg = (
                    f"'{self._directive}: start' was not followed by "
                    f"'{self._directive}: end'"
                )
                raise ValueError(msg)

            end_start, end_end, end_action = markers[i + 1]
            if end_action != "end":
                msg = (
                    f"'{self._directive}: start' "
                    f"was not followed by '{self._directive}: end'"
                )
                raise ValueError(msg)

            # Register group boundaries at parse time
            self._grouper.register_group(
                document=document,
                group_id=group_id,
                start_pos=start_start,
                end_pos=end_end,
            )

            # Create markers with group boundaries
            start_marker = _GroupMarker(
                action="start",
                group_id=group_id,
                start_pos=start_start,
                end_pos=end_end,
            )
            end_marker = _GroupMarker(
                action="end",
                group_id=group_id,
                start_pos=start_start,
                end_pos=end_end,
            )

            regions.append(
                Region(
                    start=start_start,
                    end=start_end,
                    parsed=start_marker,
                    evaluator=self._grouper,
                )
            )
            regions.append(
                Region(
                    start=end_start,
                    end=end_end,
                    parsed=end_marker,
                    evaluator=self._grouper,
                )
            )

            group_id += 1
            i += 2

        # Push evaluator at parse time (like group_all does)
        # This ensures all code blocks go through the grouper
        document.push_evaluator(evaluator=self._grouper)

        yield from regions
