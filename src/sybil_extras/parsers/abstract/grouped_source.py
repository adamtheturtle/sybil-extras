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
    count_expected_code_blocks,
    create_combined_example,
    create_combined_region,
    has_source,
)


@beartype
@dataclass(frozen=True)
class _GroupStateKey:
    """
    Key for looking up group state.
    """

    document: Document
    group_id: int


@beartype
@dataclass
class _GroupBoundary:
    """
    Boundary information for a group.
    """

    group_id: int
    start_position: int
    end_position: int


@beartype
@dataclass
class _GroupMarker:
    """
    A marker for a group start or end.
    """

    action: Literal["start", "end"]
    group_id: int
    # Store the boundaries so code blocks can determine membership
    start_position: int
    end_position: int
    # Number of code blocks expected in this group
    expected_code_blocks: int


@beartype
class _GroupState:
    """
    State for a single group.
    """

    def __init__(
        self,
        *,
        start_position: int,
        end_position: int,
        expected_code_blocks: int,
    ) -> None:
        """
        Initialize the group state.
        """
        self.start_position = start_position
        self.end_position = end_position
        self.expected_code_blocks = expected_code_blocks
        self.examples: list[Example] = []
        self.lock = threading.Lock()
        self.ready = threading.Condition(lock=self.lock)
        self.collected_count = 0


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
        # State is keyed by _GroupStateKey to allow multiple groups
        # in the same document to be processed in parallel.
        self._group_state: dict[_GroupStateKey, _GroupState] = {}
        self._group_state_lock = threading.Lock()
        self._evaluator = evaluator
        self._directive = directive
        self._pad_groups = pad_groups
        # Track group boundaries per document for determining membership
        self._group_boundaries: dict[Document, list[_GroupBoundary]] = {}
        self._group_boundaries_lock = threading.Lock()

    def register_group(
        self,
        *,
        document: Document,
        group_id: int,
        start_position: int,
        end_position: int,
        expected_code_blocks: int,
    ) -> None:
        """Register a group's boundaries for later membership lookup.

        Called at parse time, not evaluation time.

        Both locks are held together to ensure atomicity - a boundary
        and its corresponding state must be registered together without
        a gap that could be exploited by another thread.
        """
        with self._group_boundaries_lock, self._group_state_lock:
            if document not in self._group_boundaries:
                self._group_boundaries[document] = []
            self._group_boundaries[document].append(
                _GroupBoundary(
                    group_id=group_id,
                    start_position=start_position,
                    end_position=end_position,
                )
            )
            key = _GroupStateKey(document=document, group_id=group_id)
            self._group_state[key] = _GroupState(
                start_position=start_position,
                end_position=end_position,
                expected_code_blocks=expected_code_blocks,
            )

    def _find_containing_group_and_state(
        self,
        document: Document,
        position: int,
    ) -> _GroupState | None:
        """Find which group contains the given position and return its state.

        This method atomically checks boundaries and retrieves state
        while holding both locks. This prevents a TOCTOU race where
        cleanup could delete the state between finding the group
        boundary and retrieving the state.
        """
        with self._group_boundaries_lock, self._group_state_lock:
            boundaries = self._group_boundaries.get(document, [])
            for boundary in boundaries:
                if boundary.start_position < position < boundary.end_position:
                    key = _GroupStateKey(
                        document=document,
                        group_id=boundary.group_id,
                    )
                    return self._group_state[key]
        return None

    def _get_group_state(
        self,
        document: Document,
        group_id: int,
    ) -> _GroupState:
        """
        Get the state for a specific group.
        """
        key = _GroupStateKey(document=document, group_id=group_id)
        with self._group_state_lock:
            return self._group_state[key]

    def _cleanup_group_state(
        self,
        document: Document,
        group_id: int,
    ) -> None:
        """Clean up the state for a specific group.

        This method atomically cleans up both state and boundaries, and
        calls pop_evaluator if this was the last group in the document.
        Both locks are held together to prevent race conditions where
        multiple threads could both see an empty boundary list and call
        pop_evaluator.
        """
        key = _GroupStateKey(document=document, group_id=group_id)
        # Hold both locks to ensure atomic cleanup and pop_evaluator call
        with self._group_boundaries_lock, self._group_state_lock:
            del self._group_state[key]
            self._group_boundaries[document] = [
                boundary
                for boundary in self._group_boundaries[document]
                if boundary.group_id != group_id
            ]
            if not self._group_boundaries[document]:
                del self._group_boundaries[document]
                document.pop_evaluator(evaluator=self)

    def _evaluate_grouper_example(self, example: Example) -> None:
        """
        Evaluate a grouper marker.
        """
        marker: _GroupMarker = example.parsed
        state = self._get_group_state(
            document=example.document,
            group_id=marker.group_id,
        )

        with state.ready:
            if marker.action == "start":
                return

            # Wait until all expected code blocks have been collected
            while state.collected_count < state.expected_code_blocks:
                state.ready.wait()

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
                self._cleanup_group_state(
                    document=example.document,
                    group_id=marker.group_id,
                )

    def _evaluate_other_example(self, example: Example) -> None:
        """Evaluate an example that is not a group example.

        Determine group membership based on position.
        """
        # Atomically find group and get state to avoid TOCTOU race
        state = self._find_containing_group_and_state(
            document=example.document,
            position=example.region.start,
        )

        if state is None:
            raise NotEvaluated

        with state.ready:
            if has_source(example=example):
                state.examples.append(example)
                state.collected_count += 1
                state.ready.notify_all()
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
        marker_index = 0
        while marker_index < len(markers):
            start_start, start_end, start_action = markers[marker_index]
            if start_action != "start":
                msg = (
                    f"'{self._directive}: {start_action}' "
                    f"must follow '{self._directive}: start'"
                )
                raise ValueError(msg)

            if marker_index + 1 >= len(markers):
                msg = (
                    f"'{self._directive}: start' was not followed by "
                    f"'{self._directive}: end'"
                )
                raise ValueError(msg)

            end_start, end_end, end_action = markers[marker_index + 1]
            if end_action != "end":
                msg = (
                    f"'{self._directive}: start' "
                    f"was not followed by '{self._directive}: end'"
                )
                raise ValueError(msg)

            # Count code blocks in this group by examining existing examples.
            # At parse time, previous parsers have already added their regions
            # to the document, so we can count examples that fall within our
            # group boundaries.
            examples_in_group = (
                ex
                for ex in document.examples()
                if start_start < ex.region.start < end_end
            )
            expected_code_blocks = count_expected_code_blocks(
                examples=examples_in_group,
            )

            # Register group boundaries at parse time
            self._grouper.register_group(
                document=document,
                group_id=group_id,
                start_position=start_start,
                end_position=end_end,
                expected_code_blocks=expected_code_blocks,
            )

            # Create markers with group boundaries
            start_marker = _GroupMarker(
                action="start",
                group_id=group_id,
                start_position=start_start,
                end_position=end_end,
                expected_code_blocks=expected_code_blocks,
            )
            end_marker = _GroupMarker(
                action="end",
                group_id=group_id,
                start_position=start_start,
                end_position=end_end,
                expected_code_blocks=expected_code_blocks,
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
            marker_index += 2

        # Push evaluator at parse time (like group_all does)
        # This ensures all code blocks go through the grouper
        document.push_evaluator(evaluator=self._grouper)

        yield from regions
