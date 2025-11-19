"""
A parser that groups all code blocks in a MyST document.
"""

from collections import defaultdict
from collections.abc import Iterable

from sybil import Document, Example, Region
from sybil.example import NotEvaluated
from sybil.region import Lexeme
from sybil.typing import Evaluator


class _GroupAllState:
    """
    State for grouping all examples in a document.
    """

    def __init__(self) -> None:
        """
        Initialize the group all state.
        """
        self.examples: list[Example] = []

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
        has_source = "source" in example.region.lexemes
        if has_source:
            state.examples.append(example)
            return

        raise NotEvaluated

    def finalize(self, example: Example) -> None:
        """
        Finalize the grouping and evaluate all collected examples.
        """
        state = self._document_state[example.document]

        if not state.examples:
            example.document.pop_evaluator(evaluator=self)
            del self._document_state[example.document]
            return

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


class GroupAllParser:
    """
    A parser that groups all code blocks in a document without markup.
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
