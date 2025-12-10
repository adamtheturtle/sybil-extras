"""
Tests for custom norg lexers.
"""

from textwrap import dedent

from sybil import Document
from sybil.testing import check_lexer

from sybil_extras.parsers.norg.codeblock import NorgVerbatimRangedTagLexer
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


def test_verbatim_ranged_tag_lexer_no_mapping() -> None:
    """
    The verbatim ranged tag lexer works without a mapping.
    """
    lexer = NorgVerbatimRangedTagLexer(language=r"python")
    source_text = dedent(
        text="""\
        @code python
        x = 1
        @end
        """,
    )

    expected_text = "@code python\nx = 1\n@end"

    # Get the regions manually since check_lexer doesn't handle Lexeme
    # objects properly
    document = Document(text=source_text, path="sample.txt")
    regions = list(lexer(document))
    assert len(regions) == 1
    region = regions[0]
    assert expected_text == document.text[region.start : region.end]
    assert region.lexemes["language"] == "python"
    assert region.lexemes["source"].text == "x = 1\n"


def test_verbatim_ranged_tag_lexer_with_mapping() -> None:
    """
    The verbatim ranged tag lexer works with a mapping.
    """
    lexer = NorgVerbatimRangedTagLexer(
        language=r"python",
        mapping={"language": "arguments", "source": "source"},
    )
    source_text = dedent(
        text="""\
        @code python
        x = 1
        @end
        """,
    )

    expected_text = "@code python\nx = 1\n@end"

    document = Document(text=source_text, path="sample.txt")
    regions = list(lexer(document))
    assert len(regions) == 1
    region = regions[0]
    assert expected_text == document.text[region.start : region.end]
    assert region.lexemes["arguments"] == "python"
    assert region.lexemes["source"].text == "x = 1\n"


def test_verbatim_ranged_tag_lexer_no_language() -> None:
    """
    The verbatim ranged tag lexer handles code blocks without a language.
    """
    # Use a pattern that matches any language including when not specified
    lexer = NorgVerbatimRangedTagLexer(language=r".+")
    source_text = dedent(
        text="""\
        @code
        x = 1
        @end
        """,
    )

    expected_text = "@code\nx = 1\n@end"

    document = Document(text=source_text, path="sample.txt")
    regions = list(lexer(document))
    assert len(regions) == 1
    region = regions[0]
    assert expected_text == document.text[region.start : region.end]
    # Language is empty string when not specified
    assert region.lexemes["language"] == ""
    assert region.lexemes["source"].text == "x = 1\n"


def test_verbatim_ranged_tag_lexer_no_newline_after_opening() -> None:
    """
    The lexer handles the case where @end immediately follows opening tag.
    """
    lexer = NorgVerbatimRangedTagLexer(language=r".+")
    # @code python immediately followed by @end (no newline after opening)
    source_text = "@code python\n@end"

    document = Document(text=source_text, path="sample.txt")
    regions = list(lexer(document))
    assert len(regions) == 1
    region = regions[0]
    assert region.lexemes["language"] == "python"
    # Empty source since @end is right after the newline
    assert region.lexemes["source"].text == ""
