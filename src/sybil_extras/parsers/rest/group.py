"""
A group parser for reST.
"""

import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from typing import Literal

from sybil import Document, Region
from sybil.example import Example, NotEvaluated
from sybil.parsers.abstract.lexers import LexerCollection
from sybil.parsers.rest.lexers import DirectiveInCommentLexer

GROUP_ARGUMENTS_PATTERN = re.compile(pattern=r"(\w+)")


def validate_sub_regions(regions: Sequence[Region]) -> None:
    evaluators = {region.evaluator for region in regions}
    if len(evaluators) != 1:
        message = "All sub-regions of a group must have the same evaluator."
        raise ValueError(message)


@dataclass
class GroupState:
    active: bool
    last_action: Literal["start", "end"] | None = None
    examples: list[Example] | None = None


class GroupEvaluator:
    def __init__(self) -> None:
        self.document_state: dict[Document, GroupState] = {}

    def state_for(self, example: Example) -> GroupState:
        document = example.document
        if document not in self.document_state:
            self.document_state[document] = GroupState(active=True)
        return self.document_state[example.document]

    def remove(self, example: Example) -> None:
        document = example.document
        document.pop_evaluator(evaluator=self)
        del self.document_state[document]

    def install(
        self,
        example: Example,
    ) -> None:
        document = example.document
        document.push_evaluator(evaluator=self)

    def evaluate_group_example(self, example: Example) -> None:
        state = self.state_for(example=example)
        action = example.parsed

        if action not in ("start", "end"):
            raise ValueError("Bad group action: " + action)

        if state.last_action is None and action != "start":
            msg = f"'group: {action}' must follow 'group: start'"
            raise ValueError(msg)
        if state.last_action and action != "end":
            msg = (
                f"'group: {action}' cannot follow 'group: {state.last_action}'"
            )
            raise ValueError(msg)

        state.last_action = action

        if action == "start":
            self.install(example=example)
        elif action == "end":
            for inner_example in state.examples or []:
                inner_example.evaluate()
            state.examples = None
            self.remove(example=example)

    def evaluate_other_example(self, example: Example) -> None:
        state = self.state_for(example=example)
        if not state.active:
            raise NotEvaluated

        examples = state.examples or []
        state.examples = [*examples, example]

    def __call__(self, example: Example) -> None:
        if example.region.evaluator is self:
            return self.evaluate_group_example(example=example)
        return self.evaluate_other_example(example=example)


class GroupParser:
    """
    A group parser for reST.
    """

    def __init__(self, directive: str) -> None:
        """
        Args:
            directive: The name of the directive to use for grouping.
        """
        self.lexers: LexerCollection = LexerCollection(
            [DirectiveInCommentLexer(directive=directive)]
        )
        self._group_evaluator = GroupEvaluator()

    def __call__(self, document: Document) -> Iterable[Region]:
        """
        Yield regions to evaluate, grouped by start and end comments.
        """
        for lexed in self.lexers(document):
            arguments = lexed.lexemes["arguments"]
            match = GROUP_ARGUMENTS_PATTERN.match(string=arguments)
            if match is None:
                directive = lexed.lexemes.get("directive", "group")
                message = f"malformed arguments to {directive}: {arguments!r}"
                raise ValueError(message)
            (parsed,) = match.groups()

            yield Region(
                start=lexed.start,
                end=lexed.end,
                parsed=parsed,
                evaluator=self._group_evaluator,
            )
