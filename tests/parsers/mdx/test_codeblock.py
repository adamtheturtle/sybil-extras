"""Tests for MDX code block parsing.

See https://github.com/adamtheturtle/sybil-extras/issues/676
"""

from sybil import Document, Region

from sybil_extras.parsers.mdx.codeblock import CodeBlockParser


def _parse(text: str) -> list[Region]:
    """
    Parse the supplied MDX text for Python code blocks.
    """
    parser = CodeBlockParser(language="python")
    document = Document(text=text, path="doc.mdx")
    return list(parser(document=document))


class TestCodeBlockAtEOFWithoutNewline:
    """Tests for code blocks at EOF without trailing newline.

    Per the CommonMark spec: "A code block can end at the end of its
    containing block, or the end of the document, if no matching closing
    code fence is found."

    The MDX parser should recognize code blocks even when the info line
    (opening fence) appears at end-of-file without a trailing newline.
    """

    def test_info_line_at_eof_without_newline(self) -> None:
        """A code block info line at EOF without trailing newline is
        recognized.

        This tests the case where the opening fence with language is the
        last thing in the file with no newline after it.
        """
        regions = _parse(text="```python")

        assert len(regions) == 1
        assert regions[0].parsed == ""

    def test_info_line_with_attributes_at_eof_without_newline(self) -> None:
        """A code block with attributes at EOF without trailing newline.

        This tests MDX-specific attribute syntax on the info line.
        """
        regions = _parse(text='```python title="example.py"')

        assert len(regions) == 1
        assert regions[0].parsed == ""
        assert regions[0].lexemes["attributes"] == {"title": "example.py"}
