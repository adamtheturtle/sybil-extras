"""
Tests for Djot code block parsing.
"""

import re
from textwrap import dedent

from sybil import Document, Region

from sybil_extras.languages import DJOT
from sybil_extras.parsers.djot.codeblock import DjotRawFencedCodeBlockLexer


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


def test_code_block_implicitly_closed_by_container_end() -> None:
    """A code block without a closing fence is closed when its container ends.

    This follows the djot spec: "A code block ... ends with ... the end of the
    document or enclosing block, if no such line is encountered."
    """
    (region,) = _parse(
        text=dedent(
            text="""\
            > ```python
            > code in a
            > block quote

            Paragraph.
            """,
        )
    )

    assert region.parsed == "code in a\nblock quote\n"


def test_code_block_without_closing_fence_no_blockquote() -> None:
    """
    A code block without a closing fence outside a blockquote extends to EOF.
    """
    (region,) = _parse(
        text=dedent(
            text="""\
            ```python
            x = 1
            y = 2
            """,
        )
    )

    assert region.parsed == "x = 1\ny = 2\n"


def test_code_block_with_no_newline_at_end() -> None:
    """
    A code block that ends without a trailing newline.
    """
    (region,) = _parse(text="```python\nx = 1")

    assert region.parsed == "x = 1"


def test_code_block_in_nested_blockquote() -> None:
    """
    A code block in a nested blockquote is properly closed.
    """
    (region,) = _parse(
        text=dedent(
            text="""\
            > > ```python
            > > x = 1

            outside
            """,
        )
    )

    assert region.parsed == "x = 1\n"


def test_code_block_with_wrong_language() -> None:
    """
    A code block with a different language is not parsed.
    """
    regions = _parse(
        text=dedent(
            text="""\
            ```javascript
            x = 1
            ```
            """,
        )
    )

    assert len(regions) == 0


def test_code_block_empty_info_string() -> None:
    """
    A code block with no language specified is not parsed.
    """
    regions = _parse(
        text=dedent(
            text="""\
            ```
            x = 1
            ```
            """,
        )
    )

    assert len(regions) == 0


def test_code_block_in_blockquote_at_eof() -> None:
    """
    A code block in a blockquote that reaches EOF without container end.
    """
    (region,) = _parse(text="> ```python\n> x = 1\n> y = 2")

    assert region.parsed == "x = 1\ny = 2"


def test_code_block_empty_after_opening() -> None:
    """
    A code block in a blockquote with opening right at the end.
    """
    (region,) = _parse(text="> ```python\n")

    assert region.parsed == ""


def test_code_block_in_blockquote_no_newline_after_prefix_change() -> None:
    """
    A code block in blockquote where the prefix changes without newline.
    """
    (region,) = _parse(text="> ```python\n> code\nno prefix")

    assert region.parsed == "code\n"


def test_raw_lexer_without_mapping() -> None:
    """
    Test DjotRawFencedCodeBlockLexer without a mapping parameter.
    """
    lexer = DjotRawFencedCodeBlockLexer(
        info_pattern=re.compile(pattern=r"python$\n", flags=re.MULTILINE),
        mapping=None,
    )
    document = Document(text="```python\nx = 1\n```", path="test.djot")
    regions = list(lexer(document=document))

    assert len(regions) == 1
    assert regions[0].lexemes["source"].text == "x = 1\n"


def test_multiple_code_blocks_with_invalid() -> None:
    """
    Test multiple code blocks where some don't match the language filter.
    """
    text = dedent(
        text="""\
        ```javascript
        x = 1
        ```

        ```python
        y = 2
        ```
        """,
    )
    regions = _parse(text=text)

    assert len(regions) == 1
    assert regions[0].parsed == "y = 2\n"


def test_raw_lexer_skips_non_matching_and_continues() -> None:
    """Test that the lexer skips non-matching code blocks and continues.

    This hits the else branch at line 171 when maybe_region is None.
    """
    # Use DjotRawFencedCodeBlockLexer directly to ensure we hit the else branch
    lexer = DjotRawFencedCodeBlockLexer(
        info_pattern=re.compile(pattern=r"python$\n", flags=re.MULTILINE),
        mapping=None,
    )
    text = dedent(
        text="""\
        ```javascript
        x = 1
        ```

        ```python
        y = 2
        ```
        """,
    )
    document = Document(text=text, path="test.djot")
    regions = list(lexer(document=document))

    # Only the python block should match
    assert len(regions) == 1
    assert regions[0].lexemes["source"].text == "y = 2\n"


def test_fence_with_non_matching_closer() -> None:
    """Test a code block where a fence is found but doesn't match as a closer.

    This hits the branch 156->149 where match_closes_existing returns
    False and we continue looking for other fences.
    """
    # A fence in a blockquote, followed by a fence NOT in a blockquote
    # The second fence won't match because of different prefixes
    text = dedent(
        text="""\
        > ```python
        > code
        ```
        > ```
        """,
    )
    (region,) = _parse(text=text)

    # The line without "> " prefix ends the container, so the code block
    # ends before the ``` line (which is outside the blockquote)
    assert region.parsed == "code\n"


def test_region_end_respects_container_boundary_with_closing_fence() -> None:
    """Test that region end respects container boundary even when closing fence
    exists in a separate container.

    Per the Djot spec, "a code block closes...or the end of the document or
    enclosing block, if no such line is encountered."

    When a code block opens in one blockquote but lacks a closing fence within
    that container, and a matching fence appears in a *separate* blockquote
    after an empty line, the region should end at the container boundary, not
    extend to include the fence from the second blockquote.
    """
    text = dedent(
        text="""\
        > ```python
        > x = 1

        > ```
        """,
    )
    (region,) = _parse(text=text)

    # The content is correctly parsed (container ends at empty line)
    assert region.parsed == "x = 1\n"

    # The region should end where the container ends (after "> x = 1\n"),
    # not extend to include the closing fence in the separate blockquote.
    expected_region_text = "> ```python\n> x = 1\n"
    assert text[region.start : region.end] == expected_region_text
