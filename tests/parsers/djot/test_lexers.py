"""
Tests for custom djot lexers.
"""

from textwrap import dedent

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
