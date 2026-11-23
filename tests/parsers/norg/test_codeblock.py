"""Tests for Norg code block parsing."""

from textwrap import dedent

from sybil import Document, Region

from sybil_extras.evaluators._example_source import parsed_value
from sybil_extras.languages import NORG


def _parse(text: str) -> list[Region]:
    """Parse the supplied Norg text for Python code blocks."""
    parser = NORG.code_block_parser_cls(language="python", evaluator=None)
    document = Document(text=text, path="doc.norg")
    return list(parser(document=document))


def test_verbatim_ranged_tag_basic() -> None:
    """A standard verbatim ranged tag code block is parsed."""
    (region,) = _parse(
        text=dedent(
            text="""\
            @code python
            x = 1
            @end
            """,
        )
    )

    assert parsed_value(example=region) == "x = 1\n"


def test_verbatim_ranged_tag_without_language() -> None:
    """A code block without language specification is not parsed."""
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
    """A code block with a different language is not parsed."""
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
    """A multi-line code block is properly parsed."""
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

    assert parsed_value(example=region) == "x = 1\ny = 2\nz = 3\n"


def test_verbatim_ranged_tag_without_closing() -> None:
    """A code block without a closing tag is not parsed."""
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
    """A code block with leading whitespace is properly parsed."""
    (region,) = _parse(
        text=dedent(
            text="""\
              @code python
              x = 1
              @end
            """,
        )
    )

    assert parsed_value(example=region) == "x = 1\n"


def test_region_excludes_blank_lines_before_opening() -> None:
    """A region starts on its ``@code`` line, not an earlier blank
    line.
    """
    text = "Introduction\n\n\n@code python\nx = 1\n@end\n"

    (region,) = _parse(text=text)

    assert region.start == text.index("@code")
    assert text[region.start :].startswith("@code python")


def test_multiple_code_blocks() -> None:
    """Multiple code blocks in the same document are all parsed."""
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
    assert parsed_value(example=regions[0]) == "x = 1\n"
    assert parsed_value(example=regions[1]) == "y = 2\n"


def test_empty_code_block() -> None:
    """An empty code block is parsed."""
    (region,) = _parse(
        text=dedent(
            text="""\
            @code python
            @end
            """,
        )
    )

    assert parsed_value(example=region) == ""


def test_code_block_with_blank_lines() -> None:
    """A code block with blank lines is properly parsed."""
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

    assert parsed_value(example=region) == "x = 1\n\ny = 2\n"


def test_code_block_preserves_blank_lines_before_end() -> None:
    """Blank lines immediately before ``@end`` remain in the source."""
    text = "@code python\nx = 1\n\n\n@end\n"

    (region,) = _parse(text=text)

    assert parsed_value(example=region) == "x = 1\n\n\n"
    assert text[region.start : region.end] == text.rstrip("\n")


def test_nested_code_markers_in_content() -> None:
    """Code blocks can contain text that looks like markers."""
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

    assert parsed_value(example=region) == '# This is @code\nx = "@end"\n'


def test_trailing_whitespace_after_end() -> None:
    """A code block with trailing whitespace after @end is parsed."""
    # Use a raw string to preserve the trailing spaces after @end
    text = "@code python\nx = 1\n@end   \n"
    (region,) = _parse(text=text)

    assert parsed_value(example=region) == "x = 1\n"
