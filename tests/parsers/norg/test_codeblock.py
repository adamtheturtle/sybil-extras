"""
Tests for Norg code block parsing.
"""

from textwrap import dedent

from sybil import Document, Region

from sybil_extras.languages import NORG


def _parse(text: str) -> list[Region]:
    """
    Parse the supplied Norg text for Python code blocks.
    """
    parser = NORG.code_block_parser_cls(language="python")
    document = Document(text=text, path="doc.norg")
    return list(parser(document=document))


def test_verbatim_ranged_tag_basic() -> None:
    """
    A standard verbatim ranged tag code block is parsed.
    """
    (region,) = _parse(
        text=dedent(
            text="""\
            @code python
            x = 1
            @end
            """,
        )
    )

    assert region.parsed == "x = 1\n"


def test_verbatim_ranged_tag_without_language() -> None:
    """
    A code block without language specification is not parsed.
    """
    regions = _parse(
        text=dedent(
            text="""\
            @code
            x = 1
            @end
            """,
        )
    )

    assert len(regions) == 0


def test_verbatim_ranged_tag_wrong_language() -> None:
    """
    A code block with a different language is not parsed.
    """
    regions = _parse(
        text=dedent(
            text="""\
            @code javascript
            x = 1
            @end
            """,
        )
    )

    assert len(regions) == 0


def test_verbatim_ranged_tag_multiline() -> None:
    """
    A multi-line code block is properly parsed.
    """
    (region,) = _parse(
        text=dedent(
            text="""\
            @code python
            x = 1
            y = 2
            z = 3
            @end
            """,
        )
    )

    assert region.parsed == "x = 1\ny = 2\nz = 3\n"


def test_verbatim_ranged_tag_without_closing() -> None:
    """
    A code block without a closing tag is not parsed.
    """
    regions = _parse(
        text=dedent(
            text="""\
            @code python
            x = 1
            """,
        )
    )

    assert len(regions) == 0


def test_verbatim_ranged_tag_with_leading_whitespace() -> None:
    """
    A code block with leading whitespace is properly parsed.
    """
    (region,) = _parse(
        text=dedent(
            text="""\
              @code python
              x = 1
              @end
            """,
        )
    )

    assert region.parsed == "x = 1\n"


def test_multiple_code_blocks() -> None:
    """
    Multiple code blocks in the same document are all parsed.
    """
    regions = _parse(
        text=dedent(
            text="""\
            @code python
            x = 1
            @end

            Some text in between.

            @code python
            y = 2
            @end
            """,
        )
    )

    expected_region_count = 2
    assert len(regions) == expected_region_count
    assert regions[0].parsed == "x = 1\n"
    assert regions[1].parsed == "y = 2\n"


def test_empty_code_block() -> None:
    """
    An empty code block is parsed.
    """
    (region,) = _parse(
        text=dedent(
            text="""\
            @code python
            @end
            """,
        )
    )

    assert region.parsed == ""


def test_code_block_with_blank_lines() -> None:
    """
    A code block with blank lines is properly parsed.
    """
    (region,) = _parse(
        text=dedent(
            text="""\
            @code python
            x = 1

            y = 2
            @end
            """,
        )
    )

    assert region.parsed == "x = 1\n\ny = 2\n"


def test_nested_code_markers_in_content() -> None:
    """
    Code blocks can contain text that looks like markers.
    """
    (region,) = _parse(
        text=dedent(
            text="""\
            @code python
            # This is @code
            x = "@end"
            @end
            """,
        )
    )

    assert region.parsed == '# This is @code\nx = "@end"\n'


def test_trailing_whitespace_after_end() -> None:
    """
    A code block with trailing whitespace after @end is parsed.
    """
    # Use a raw string to preserve the trailing spaces after @end
    text = "@code python\nx = 1\n@end   \n"
    (region,) = _parse(text=text)

    assert region.parsed == "x = 1\n"
