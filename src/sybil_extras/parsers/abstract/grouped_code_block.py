"""
A group parser for reST.
"""

from collections import defaultdict
from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from sybil import Document, Example, Region
from sybil.parsers.abstract.lexers import LexerCollection
from sybil.typing import Evaluator, Lexer


@dataclass
class _GroupState:
    """
    Group state.
    """

    combined_text: str | None = None


class _Grouper:
    """
    Group code blocks.
    """

    def __init__(self, evaluator: Evaluator) -> None:
        """
        Args:
            evaluator: The evaluator to use for evaluating the combined region.
        """
        self._document_state: dict[Document, _GroupState] = defaultdict(
            _GroupState
        )
        self._evaluator = evaluator

    def _evaluate_grouper_example(self, example: Example) -> None:
        """
        Evaluate a grouper marker.
        """
        state = self._document_state[example.document]
        action = example.parsed

        if action == "start":
            example.document.push_evaluator(evaluator=self)
            return

        if state.combined_text is not None:
            region = Region(
                start=example.region.start,
                end=example.region.end,
                parsed=state.combined_text,
                evaluator=self._evaluator,
                lexemes=example.region.lexemes,
            )
            new_example = Example(
                document=example.document,
                line=example.line,
                column=example.column,
                region=region,
                namespace=example.namespace,
            )
            self._evaluator(new_example)

        example.document.pop_evaluator(evaluator=self)
        del self._document_state[example.document]

    def _evaluate_other_example(self, example: Example) -> None:
        """
        Evaluate an example that is not a group example.
        """
        state = self._document_state[example.document]

        if "source" in example.region.lexemes:
            if state.combined_text is None:
                state.combined_text = example.parsed
            else:
                state.combined_text += example.parsed

    def __call__(self, /, example: Example) -> None:
        """
        Call the evaluator.
        """
        # We use ``id`` equivalence rather than ``is`` to avoid a
        # ``pyright`` error.
        if id(example.region.evaluator) == id(self):
            self._evaluate_grouper_example(example=example)
            return

        self._evaluate_other_example(example=example)

    # Satisfy vulture.
    _caller = __call__


class AbstractGroupedCodeBlockParser:
    """
    An abstract parser for grouping code blocks.
    """

    def __init__(self, lexers: Sequence[Lexer], evaluator: Evaluator) -> None:
        """
        Args:
            lexers: The lexers to use to find regions.
            evaluator: The evaluator to use for evaluating the combined region.
        """
        self._lexers: LexerCollection = LexerCollection(lexers)
        self._grouper: _Grouper = _Grouper(evaluator=evaluator)

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
