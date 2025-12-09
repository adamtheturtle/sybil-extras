"""
Tests for Djot code block parsing.
"""

from textwrap import dedent

from sybil import Document, Region

from sybil_extras.languages import DJOT


def _parse(text: str) -> list[Region]:
    """
    Parse the supplied Djot text for Python code blocks.
    """
    parser = DJOT.code_block_parser_cls(language="python")
    document = Document(text=text, path="doc.djot")
    return list(parser(document=document))


def test_fenced_code_block_outside_blockquote() -> None:
    """
    A standard fenced code block is parsed.
    """
    (region,) = _parse(
        text=dedent(
            text="""\
            ```python
            x = 1
            ```
            """,
        )
    )

    assert region.parsed == "x = 1\n"


def test_code_block_in_blockquote_without_closing_fence() -> None:
    """
    A Djot code block can be closed by the end of its blockquote.
    """
    (region,) = _parse(
        text=dedent(
            text="""\
            > ```python
            > x = 1
            > y = 2

            outside block quote
            """,
        )
    )

    assert region.parsed == "x = 1\ny = 2\n"
