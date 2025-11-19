"""
A group parser for reST.
"""

from collections import defaultdict
from collections.abc import Iterable, Sequence
from typing import Literal

from sybil import Document, Example, Region
from sybil.example import NotEvaluated
from sybil.parsers.abstract.lexers import LexerCollection
from sybil.typing import Evaluator, Lexer

from ._grouping_utils import (
    create_combined_example,
    create_combined_region,
    has_source,
)


class _GroupState:
    """
    Group state.
    """

    def __init__(self) -> None:
        """
        Initialize the group state.
        """
        self.last_action: Literal["start", "end"] | None = None
        self.examples: Sequence[Example] = []


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
        self._document_state: dict[Document, _GroupState] = defaultdict(
            _GroupState
        )
        self._evaluator = evaluator
        self._directive = directive
        self._pad_groups = pad_groups

    def _evaluate_grouper_example(self, example: Example) -> None:
        """
        Evaluate a grouper marker.
        """
        state = self._document_state[example.document]
        action = example.parsed

        if action == "start":
            if state.last_action == "start":
                msg = (
                    f"'{self._directive}: start' "
                    f"must be followed by '{self._directive}: end'"
                )
                raise ValueError(msg)
            example.document.push_evaluator(evaluator=self)
            state.last_action = action
            return

        if state.last_action != "start":
            msg = (
                f"'{self._directive}: {action}' "
                f"must follow '{self._directive}: start'"
            )
            raise ValueError(msg)

        if state.examples:
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
        del self._document_state[example.document]
        state.last_action = action

    def _evaluate_other_example(self, example: Example) -> None:
        """
        Evaluate an example that is not a group example.
        """
        state = self._document_state[example.document]

        if has_source(example=example):
            state.examples = [*state.examples, example]
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

    def __call__(self, document: Document) -> Iterable[Region]:
        """
        Yield regions to evaluate, grouped by start and end comments.
        """
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

            yield Region(
                start=lexed.start,
                end=lexed.end,
                parsed=arguments,
                evaluator=self._grouper,
            )
