"""
A group parser for reST.
"""

import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from sybil import Document, Example, Region
from sybil.parsers.abstract.lexers import LexerCollection
from sybil.typing import Evaluator, Lexer

GROUP_ARGUMENTS_PATTERN = re.compile(pattern=r"(\w+)")


@dataclass
class _GroupState:
    """
    Skip state.
    """

    last_action: str | None = None
    combined_text: str | None = None


class _Grouper:
    """
    A skipper.
    """

    def __init__(self, evaluator: Evaluator) -> None:
        """
        Add document state.
        """
        self.document_state: dict[Document, _GroupState] = {}
        self.evaluator = evaluator

    def state_for(self, document: Document) -> _GroupState:
        """
        Get the state for this document.
        """
        if document not in self.document_state:
            self.document_state[document] = _GroupState()
        return self.document_state[document]

    def evaluate_skip_example(self, example: Example) -> None:
        """
        Evaluate a skip example.
        """
        state = self.state_for(document=example.document)
        (action,) = example.parsed

        if action not in ("start", "end"):
            raise ValueError("Bad skip action: " + action)
        if state.last_action is None and action not in ("start",):
            msg = f"'skip: {action}' must follow 'skip: start'"
            raise ValueError(msg)
        if state.last_action and action != "end":
            msg = f"'skip: {action}' cannot follow 'skip: {state.last_action}'"
            raise ValueError(msg)

        state.last_action = action

        if action == "start":
            example.document.push_evaluator(evaluator=self)
        elif action == "end":
            if state.combined_text is not None:
                region = Region(
                    start=example.region.start,
                    end=example.region.end,
                    parsed=state.combined_text,
                    evaluator=self.evaluator,
                    lexemes=example.region.lexemes,
                )
                new_example = Example(
                    document=example.document,
                    line=example.line,
                    column=example.column,
                    region=region,
                    namespace=example.namespace,
                )
                self.evaluator(new_example)
            example.document.pop_evaluator(evaluator=self)
            del self.document_state[example.document]

    def evaluate_other_example(self, example: Example) -> None:
        """
        Evaluate an example that is not a skip example.
        """
        state = self.state_for(document=example.document)

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
        # Pyright error.
        if id(example.region.evaluator) == id(self):
            self.evaluate_skip_example(example=example)
            return

        self.evaluate_other_example(example=example)

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
        self.lexers: LexerCollection = LexerCollection(lexers)
        self.grouper: _Grouper = _Grouper(evaluator=evaluator)

    def __call__(self, document: Document) -> Iterable[Region]:
        """
        Yield regions to evaluate, grouped by start and end comments.
        """
        for lexed in self.lexers(document):
            arguments = lexed.lexemes["arguments"]
            match = GROUP_ARGUMENTS_PATTERN.match(string=arguments)
            if match is None:
                directive = lexed.lexemes.get("directive", "skip")
                msg = f"malformed arguments to {directive}: {arguments!r}"
                raise ValueError(msg)

            yield Region(
                start=lexed.start,
                end=lexed.end,
                parsed=match.groups(),
                evaluator=self.grouper,
            )
