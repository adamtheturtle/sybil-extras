"""
A group parser for reST.
"""

from collections import defaultdict
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from typing import Literal

from sybil import Document, Example, Region
from sybil.example import NotEvaluated
from sybil.parsers.abstract.lexers import LexerCollection
from sybil.region import Lexeme
from sybil.typing import Evaluator, Lexer


@dataclass
class _GroupState:
    """
    Group state.
    """

    last_action: Literal["start", "end"] | None = None
    examples: Sequence[Example] = field(default_factory=list)

    def combine_text(self, *, pad_groups: bool) -> Lexeme:
        """Get the combined text.

        Pad the examples with newlines to ensure that line numbers in
        error messages match the line numbers in the source.
        """
        result = self.examples[0].parsed
        for example in self.examples[1:]:
            existing_lines = len(result.text.splitlines())
            if pad_groups:
                padding_lines = (
                    example.line - self.examples[0].line - existing_lines
                )
            else:
                padding_lines = 1

            padding = "\n" * padding_lines
            result = Lexeme(
                text=result.text + padding + example.parsed,
                offset=result.offset,
                line_offset=result.line_offset,
            )

        return Lexeme(
            text=result.text,
            offset=result.offset,
            line_offset=result.line_offset,
        )


class _Grouper:
    """
    Group code blocks.
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
            region = Region(
                start=state.examples[0].region.start,
                end=state.examples[-1].region.end,
                parsed=state.combine_text(pad_groups=self._pad_groups),
                evaluator=self._evaluator,
                lexemes=example.region.lexemes,
            )
            new_example = Example(
                document=example.document,
                line=state.examples[0].line,
                column=state.examples[0].column,
                region=region,
                namespace=example.namespace,
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

        is_code_block = "source" in example.region.lexemes

        if is_code_block:
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


class AbstractGroupedCodeBlockParser:
    """
    An abstract parser for grouping code blocks.
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
