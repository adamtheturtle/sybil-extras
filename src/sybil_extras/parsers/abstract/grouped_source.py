"""
An abstract parser for grouping blocks of source code.
"""

import re
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
    # Track how many code blocks are expected in this group
    expected_code_blocks: int


@beartype
@dataclass
class _GroupBoundary:
    """
    Boundary information for a group.
    """

    group_id: int
    start_pos: int
    end_pos: int


@beartype
class _GroupState:
    """
    State for a single group.
    """

    def __init__(
        self,
        *,
        start_pos: int,
        end_pos: int,
        expected_code_blocks: int,
    ) -> None:
        """
        Initialize the group state.
        """
        self.start_pos = start_pos
        self.end_pos = end_pos
        self.expected_code_blocks = expected_code_blocks
        self.examples: list[Example] = []
        self.lock = threading.Lock()
        self.ready = threading.Condition(self.lock)
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
        # State is keyed by (document, group_id) to allow multiple groups
        # in the same document to be processed in parallel.
        self._group_state: dict[tuple[Document, int], _GroupState] = {}
        self._group_state_lock = threading.Lock()
        self._evaluator = evaluator
        self._directive = directive
        self._pad_groups = pad_groups
        # Track group boundaries per document for determining membership
        self._group_boundaries: dict[Document, list[_GroupBoundary]] = {}
        self._group_boundaries_lock = threading.Lock()
        # Track active groups per document for cleanup
        self._active_group_count: dict[Document, int] = {}
        self._active_group_lock = threading.Lock()

    def register_group(
        self,
        document: Document,
        group_id: int,
        start_pos: int,
        end_pos: int,
        expected_code_blocks: int,
    ) -> None:
        """Register a group's boundaries for later membership lookup.

        Called at parse time, not evaluation time.
        """
        boundary = _GroupBoundary(
            group_id=group_id,
            start_pos=start_pos,
            end_pos=end_pos,
        )
        with self._group_boundaries_lock:
            if document not in self._group_boundaries:
                self._group_boundaries[document] = []
            self._group_boundaries[document].append(boundary)
        # Pre-create the group state
        key = (document, group_id)
        with self._group_state_lock:
            if key not in self._group_state:
                self._group_state[key] = _GroupState(
                    start_pos=start_pos,
                    end_pos=end_pos,
                    expected_code_blocks=expected_code_blocks,
                )
        # Track active group count
        with self._active_group_lock:
            self._active_group_count[document] = (
                self._active_group_count.get(document, 0) + 1
            )

    def _find_containing_group(
        self,
        document: Document,
        position: int,
    ) -> int | None:
        """
        Find which group contains the given position.
        """
        with self._group_boundaries_lock:
            boundaries = self._group_boundaries.get(document, [])
            for boundary in boundaries:
                if boundary.start_pos < position < boundary.end_pos:
                    return boundary.group_id
        return None

    def _get_group_state(
        self,
        document: Document,
        group_id: int,
    ) -> _GroupState | None:
        """
        Get the state for a specific group if it exists.
        """
        key = (document, group_id)
        with self._group_state_lock:
            return self._group_state.get(key)

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
                    boundary
                    for boundary in self._group_boundaries[document]
                    if boundary.group_id != group_id
                ]
                if not self._group_boundaries[document]:
                    del self._group_boundaries[document]
        # Track active group count and pop evaluator when done
        with self._active_group_lock:
            if document in self._active_group_count:
                self._active_group_count[document] -= 1
                if self._active_group_count[document] <= 0:
                    del self._active_group_count[document]
                    document.pop_evaluator(evaluator=self)

    def _evaluate_grouper_example(self, example: Example) -> None:
        """
        Evaluate a grouper marker.
        """
        marker: _GroupMarker = example.parsed

        if marker.action == "start":
            # Start markers don't need to do anything - group is already
            # registered at parse time
            return

        # End marker - wait for all code blocks to be collected, then process
        state = self._get_group_state(example.document, marker.group_id)
        if state is None:
            return

        with state.ready:
            # Wait until all expected code blocks have been collected.
            # Use a timeout to handle cases where some blocks are skipped
            # and will never be collected.
            timeout_seconds = 0.1
            while state.collected_count < state.expected_code_blocks:
                if not state.ready.wait(timeout=timeout_seconds):
                    # Timeout - proceed with what we have (some blocks may
                    # have been skipped)
                    break

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
        if state is None:
            raise NotEvaluated

        with state.ready:
            if has_source(example=example):
                state.examples.append(example)
                state.collected_count += 1
                # Signal that a code block has been collected
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
                    f"'{self._directive}: start' was not followed by "
                    f"'{self._directive}: end'"
                )
                raise ValueError(msg)

            # Count code blocks in this group's range by scanning document
            # We look for patterns that indicate code blocks
            group_text = document.text[start_end:end_start]
            # Count occurrences of code block markers
            # This is a heuristic - we count triple backticks (divided by 2
            # since each block has open + close), or code-block directives
            backtick_count = len(re.findall(r"```", group_text))
            directive_count = len(
                re.findall(
                    r"\.\. code-block::|@code\b|#\+begin_src",
                    group_text,
                    re.IGNORECASE,
                )
            )
            code_block_count = backtick_count // 2 + directive_count

            # Register group boundaries at parse time
            self._grouper.register_group(
                document=document,
                group_id=group_id,
                start_pos=start_start,
                end_pos=end_end,
                expected_code_blocks=code_block_count,
            )

            # Create markers with group boundaries
            start_marker = _GroupMarker(
                action="start",
                group_id=group_id,
                start_pos=start_start,
                end_pos=end_end,
                expected_code_blocks=code_block_count,
            )
            end_marker = _GroupMarker(
                action="end",
                group_id=group_id,
                start_pos=start_start,
                end_pos=end_end,
                expected_code_blocks=code_block_count,
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
