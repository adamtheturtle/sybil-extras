"""
Tests for custom djot lexers.
"""

from textwrap import dedent

from sybil import Document
from sybil.testing import check_lexer

from sybil_extras.parsers.djot.lexers import DirectiveInDjotCommentLexer


def test_directive_with_argument() -> None:
    """
    A directive with an argument is captured along with its text.
    """
    lexer = DirectiveInDjotCommentLexer(directive="group", arguments=r".+")
    source_text = dedent(
        text="""\
        Before
        {% group: start %}
        After
        """,
    )

    expected_text = "{% group: start %}"
    expected_lexemes = {"directive": "group", "arguments": "start"}

    check_lexer(
        lexer=lexer,
        source_text=source_text,
        expected_text=expected_text,
        expected_lexemes=expected_lexemes,
    )


def test_directive_without_argument() -> None:
    """
    A directive without an argument yields an empty arguments lexeme.
    """
    lexer = DirectiveInDjotCommentLexer(directive="skip")
    source_text = "{% skip %}\n"

    expected_text = "{% skip %}"
    expected_lexemes = {"directive": "skip", "arguments": ""}

    check_lexer(
        lexer=lexer,
        source_text=source_text,
        expected_text=expected_text,
        expected_lexemes=expected_lexemes,
    )


def test_directive_with_mapping() -> None:
    """
    Lexeme names can be remapped when requested.
    """
    lexer = DirectiveInDjotCommentLexer(
        directive="custom",
        arguments=r".*",
        mapping={"directive": "name", "arguments": "argument"},
    )
    source_text = "{% custom: spaced argument %}"

    expected_text = source_text
    expected_lexemes = {"name": "custom", "argument": "spaced argument"}

    check_lexer(
        lexer=lexer,
        source_text=source_text,
        expected_text=expected_text,
        expected_lexemes=expected_lexemes,
    )


def test_directive_stops_at_first_closing_delimiter() -> None:
    """Djot comments end at the first ``%}``, so text after it is not captured.

    This tests that ``{% group: foo %} bar %}`` captures only ``foo`` as
    the argument, not ``foo %} bar``.
    """
    lexer = DirectiveInDjotCommentLexer(directive="group", arguments=r".+")
    source_text = "{% group: foo %} bar %}\n"

    expected_text = "{% group: foo %}"
    expected_lexemes = {"directive": "group", "arguments": "foo"}

    check_lexer(
        lexer=lexer,
        source_text=source_text,
        expected_text=expected_text,
        expected_lexemes=expected_lexemes,
    )


def test_arguments_pattern_filters_matches() -> None:
    """The arguments pattern filters out directives that don't match.

    With ``arguments=r".+"``, a directive with an empty argument should
    not be matched.
    """
    lexer = DirectiveInDjotCommentLexer(directive="group", arguments=r".+")
    source_text = "{% group: %}\n"

    document = Document(text=source_text, path="sample.txt")
    regions = list(lexer(document))
    assert len(regions) == 0


def test_argument_with_percent_sign() -> None:
    """
    Arguments can contain percent signs that are not followed by ``}``.
    """
    lexer = DirectiveInDjotCommentLexer(directive="group", arguments=r".+")
    source_text = "{% group: 50% off %}\n"

    expected_text = "{% group: 50% off %}"
    expected_lexemes = {"directive": "group", "arguments": "50% off"}

    check_lexer(
        lexer=lexer,
        source_text=source_text,
        expected_text=expected_text,
        expected_lexemes=expected_lexemes,
    )


def test_arguments_pattern_with_alternation() -> None:
    """Alternation in arguments pattern matches exactly, not partially.

    With ``arguments=r"start|end"``, only "start" or "end" should match,
    not "starting" or "the end".
    """
    lexer = DirectiveInDjotCommentLexer(
        directive="group",
        arguments=r"start|end",
    )

    # "start" should match
    document = Document(text="{% group: start %}\n", path="sample.txt")
    regions = list(lexer(document))
    assert len(regions) == 1
    assert regions[0].lexemes["arguments"] == "start"

    # "end" should match
    document = Document(text="{% group: end %}\n", path="sample.txt")
    regions = list(lexer(document))
    assert len(regions) == 1
    assert regions[0].lexemes["arguments"] == "end"

    # "starting" should NOT match
    document = Document(text="{% group: starting %}\n", path="sample.txt")
    regions = list(lexer(document))
    assert len(regions) == 0

    # "the end" should NOT match
    document = Document(text="{% group: the end %}\n", path="sample.txt")
    regions = list(lexer(document))
    assert len(regions) == 0
