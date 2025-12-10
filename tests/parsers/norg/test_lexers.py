"""
Tests for custom norg lexers.
"""

from textwrap import dedent

from sybil.testing import check_lexer

from sybil_extras.parsers.norg.lexers import DirectiveInNorgCommentLexer


def test_directive_with_argument() -> None:
    """
    A directive with an argument is captured along with its text.
    """
    lexer = DirectiveInNorgCommentLexer(directive="group", arguments=r".+")
    source_text = dedent(
        text="""\
        Before
        .group: start
        After
        """,
    )

    expected_text = ".group: start"
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
    lexer = DirectiveInNorgCommentLexer(directive="skip")
    source_text = ".skip\n"

    expected_text = ".skip"
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
    lexer = DirectiveInNorgCommentLexer(
        directive="custom",
        arguments=r".*",
        mapping={"directive": "name", "arguments": "argument"},
    )
    source_text = ".custom: spaced argument"

    expected_text = source_text
    expected_lexemes = {"name": "custom", "argument": "spaced argument"}

    check_lexer(
        lexer=lexer,
        source_text=source_text,
        expected_text=expected_text,
        expected_lexemes=expected_lexemes,
    )


def test_directive_with_leading_whitespace() -> None:
    """
    A directive with leading whitespace is matched.
    """
    lexer = DirectiveInNorgCommentLexer(directive="skip")
    source_text = "  .skip\n"

    expected_text = "  .skip"
    expected_lexemes = {"directive": "skip", "arguments": ""}

    check_lexer(
        lexer=lexer,
        source_text=source_text,
        expected_text=expected_text,
        expected_lexemes=expected_lexemes,
    )
