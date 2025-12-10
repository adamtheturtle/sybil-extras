"""
Tests for the code_block_writer module.
"""

import textwrap
from pathlib import Path

from sybil import Example, Sybil

from sybil_extras.evaluators.code_block_writer import (
    CodeBlockWriterEvaluator,
    lstrip_padding,
    overwrite_example_content,
)
from sybil_extras.languages import (
    DJOT,
    MARKDOWN,
    MDX,
    MYST,
    MYST_PERCENT_COMMENTS,
    NORG,
    RESTRUCTUREDTEXT,
    MarkupLanguage,
)


class TestLstripPadding:
    """
    Tests for the lstrip_padding function.
    """

    def test_removes_specified_newlines(self) -> None:
        """
        Removes the specified number of leading newlines.
        """
        content = "\n\n\ncode"
        result = lstrip_padding(content=content, padding_lines=2)
        assert result == "\ncode"

    def test_removes_all_when_fewer_exist(self) -> None:
        """
        Removes all newlines when fewer than requested exist.
        """
        content = "\ncode"
        result = lstrip_padding(content=content, padding_lines=5)
        assert result == "code"

    def test_no_newlines_to_remove(self) -> None:
        """
        Returns content unchanged when no leading newlines.
        """
        content = "code"
        result = lstrip_padding(content=content, padding_lines=2)
        assert result == "code"

    def test_zero_padding_lines(self) -> None:
        """
        Returns content unchanged when padding_lines is zero.
        """
        content = "\n\ncode"
        result = lstrip_padding(content=content, padding_lines=0)
        assert result == "\n\ncode"

    def test_empty_string(self) -> None:
        """
        Handles empty string.
        """
        content = ""
        result = lstrip_padding(content=content, padding_lines=2)
        assert result == ""


class TestOverwriteExampleContent:
    """
    Tests for the overwrite_example_content function.
    """

    def test_overwrites_content(
        self,
        tmp_path: Path,
        markup_language: MarkupLanguage,
    ) -> None:
        """
        Content is overwritten in the source file.
        """
        markdown_content = textwrap.dedent(
            text="""\
            Not in code block

            ```python
            x = 2 + 2
            assert x == 4
            ```
            """
        )
        myst_content = textwrap.dedent(
            text="""\
            Not in code block

            ```{code} python
            x = 2 + 2
            assert x == 4
            ```
            """
        )
        norg_content = textwrap.dedent(
            text="""\
            Not in code block

            @code python
            x = 2 + 2
            assert x == 4
            @end
            """
        )
        original_content = {
            RESTRUCTUREDTEXT: textwrap.dedent(
                text="""\
                Not in code block

                .. code-block:: python

                   x = 2 + 2
                   assert x == 4
                """
            ),
            MARKDOWN: markdown_content,
            MDX: markdown_content,
            DJOT: markdown_content,
            NORG: norg_content,
            MYST: myst_content,
            MYST_PERCENT_COMMENTS: myst_content,
        }[markup_language]

        source_file = tmp_path / "source_file.txt"
        source_file.write_text(data=original_content, encoding="utf-8")

        parser = markup_language.code_block_parser_cls(language="python")
        sybil = Sybil(parsers=[parser])
        document = sybil.parse(path=source_file)
        (example,) = document.examples()

        overwrite_example_content(
            example=example,
            new_content="foobar",
        )

        markdown_expected = textwrap.dedent(
            text="""\
            Not in code block

            ```python
            foobar
            ```
            """
        )
        myst_expected = textwrap.dedent(
            text="""\
            Not in code block

            ```{code} python
            foobar
            ```
            """
        )
        norg_expected = textwrap.dedent(
            text="""\
            Not in code block

            @code python
            foobar
            @end
            """
        )
        expected_content = {
            RESTRUCTUREDTEXT: textwrap.dedent(
                text="""\
                Not in code block

                .. code-block:: python

                   foobar
                """
            ),
            MARKDOWN: markdown_expected,
            MDX: markdown_expected,
            DJOT: markdown_expected,
            NORG: norg_expected,
            MYST: myst_expected,
            MYST_PERCENT_COMMENTS: myst_expected,
        }[markup_language]

        assert source_file.read_text(encoding="utf-8") == expected_content

    def test_no_change_when_content_same(self, tmp_path: Path) -> None:
        """
        File is not modified when content is the same.
        """
        content = textwrap.dedent(
            text="""\
            Not in code block

            ```python
            x = 2 + 2
            ```
            """
        )
        source_file = tmp_path / "source_file.txt"
        source_file.write_text(data=content, encoding="utf-8")
        original_mtime = source_file.stat().st_mtime

        parser = MARKDOWN.code_block_parser_cls(language="python")
        sybil = Sybil(parsers=[parser])
        document = sybil.parse(path=source_file)
        (example,) = document.examples()

        overwrite_example_content(
            example=example,
            new_content="x = 2 + 2\n",
        )

        assert source_file.stat().st_mtime == original_mtime

    def test_updates_subsequent_regions(self, tmp_path: Path) -> None:
        """
        Subsequent region offsets are updated when content changes size.
        """
        content = textwrap.dedent(
            text="""\
            ```python
            x = 1
            ```

            ```python
            y = 2
            ```
            """
        )
        source_file = tmp_path / "source_file.txt"
        source_file.write_text(data=content, encoding="utf-8")

        parser = MARKDOWN.code_block_parser_cls(language="python")
        sybil = Sybil(parsers=[parser])
        document = sybil.parse(path=source_file)
        first_example, second_example = document.examples()

        # Make the first block much larger
        overwrite_example_content(
            example=first_example,
            new_content="x = 1\nx = 2\nx = 3\nx = 4\n",
        )

        # The second block should still be valid after the offset update
        overwrite_example_content(
            example=second_example,
            new_content="z = 3\n",
        )

        expected_content = textwrap.dedent(
            text="""\
            ```python
            x = 1
            x = 2
            x = 3
            x = 4
            ```

            ```python
            z = 3
            ```
            """
        )
        assert source_file.read_text(encoding="utf-8") == expected_content


class TestCodeBlockWriterEvaluator:
    """
    Tests for the CodeBlockWriterEvaluator class.
    """

    def test_writes_modified_content(
        self,
        tmp_path: Path,
        markup_language: MarkupLanguage,
    ) -> None:
        """
        Writes modified content from namespace to source file.
        """
        markdown_content = textwrap.dedent(
            text="""\
            Not in code block

            ```python
            original
            ```
            """
        )
        myst_content = textwrap.dedent(
            text="""\
            Not in code block

            ```{code} python
            original
            ```
            """
        )
        norg_content = textwrap.dedent(
            text="""\
            Not in code block

            @code python
            original
            @end
            """
        )
        original_content = {
            RESTRUCTUREDTEXT: textwrap.dedent(
                text="""\
                Not in code block

                .. code-block:: python

                   original
                """
            ),
            MARKDOWN: markdown_content,
            MDX: markdown_content,
            DJOT: markdown_content,
            NORG: norg_content,
            MYST: myst_content,
            MYST_PERCENT_COMMENTS: myst_content,
        }[markup_language]

        source_file = tmp_path / "source_file.txt"
        source_file.write_text(data=original_content, encoding="utf-8")

        def modifying_evaluator(example: Example) -> None:
            """
            Store modified content in namespace.
            """
            example.document.namespace["modified_content"] = "modified"

        writer_evaluator = CodeBlockWriterEvaluator(
            evaluator=modifying_evaluator
        )
        parser = markup_language.code_block_parser_cls(
            language="python",
            evaluator=writer_evaluator,
        )
        sybil = Sybil(parsers=[parser])
        document = sybil.parse(path=source_file)
        (example,) = document.examples()
        example.evaluate()

        markdown_expected = textwrap.dedent(
            text="""\
            Not in code block

            ```python
            modified
            ```
            """
        )
        myst_expected = textwrap.dedent(
            text="""\
            Not in code block

            ```{code} python
            modified
            ```
            """
        )
        norg_expected = textwrap.dedent(
            text="""\
            Not in code block

            @code python
            modified
            @end
            """
        )
        expected_content = {
            RESTRUCTUREDTEXT: textwrap.dedent(
                text="""\
                Not in code block

                .. code-block:: python

                   modified
                """
            ),
            MARKDOWN: markdown_expected,
            MDX: markdown_expected,
            DJOT: markdown_expected,
            NORG: norg_expected,
            MYST: myst_expected,
            MYST_PERCENT_COMMENTS: myst_expected,
        }[markup_language]

        assert source_file.read_text(encoding="utf-8") == expected_content
        # Namespace key is cleared after write
        assert "modified_content" not in document.namespace

    def test_no_write_when_content_unchanged(self, tmp_path: Path) -> None:
        """
        Does not write when modified content matches original.
        """
        content = textwrap.dedent(
            text="""\
            ```python
            original
            ```
            """
        )
        source_file = tmp_path / "source_file.txt"
        source_file.write_text(data=content, encoding="utf-8")
        original_mtime = source_file.stat().st_mtime

        def same_content_evaluator(example: Example) -> None:
            """
            Store same content in namespace.
            """
            example.document.namespace["modified_content"] = "original\n"

        writer_evaluator = CodeBlockWriterEvaluator(
            evaluator=same_content_evaluator
        )
        parser = MARKDOWN.code_block_parser_cls(
            language="python",
            evaluator=writer_evaluator,
        )
        sybil = Sybil(parsers=[parser])
        document = sybil.parse(path=source_file)
        (example,) = document.examples()
        example.evaluate()

        assert source_file.stat().st_mtime == original_mtime

    def test_no_write_when_no_namespace_key(self, tmp_path: Path) -> None:
        """
        Does not write when namespace key is not set.
        """
        content = textwrap.dedent(
            text="""\
            ```python
            original
            ```
            """
        )
        source_file = tmp_path / "source_file.txt"
        source_file.write_text(data=content, encoding="utf-8")
        original_mtime = source_file.stat().st_mtime

        def no_modify_evaluator(example: Example) -> None:
            """
            Do not store modified content.
            """
            del example

        writer_evaluator = CodeBlockWriterEvaluator(
            evaluator=no_modify_evaluator
        )
        parser = MARKDOWN.code_block_parser_cls(
            language="python",
            evaluator=writer_evaluator,
        )
        sybil = Sybil(parsers=[parser])
        document = sybil.parse(path=source_file)
        (example,) = document.examples()
        example.evaluate()

        assert source_file.stat().st_mtime == original_mtime

    def test_custom_namespace_key(self, tmp_path: Path) -> None:
        """
        Uses custom namespace key for modified content.
        """
        content = textwrap.dedent(
            text="""\
            ```python
            original
            ```
            """
        )
        source_file = tmp_path / "source_file.txt"
        source_file.write_text(data=content, encoding="utf-8")

        custom_key = "custom_modified"

        def modifying_evaluator(example: Example) -> None:
            """
            Store modified content with custom key.
            """
            example.document.namespace[custom_key] = "modified"

        writer_evaluator = CodeBlockWriterEvaluator(
            evaluator=modifying_evaluator,
            namespace_key=custom_key,
        )
        parser = MARKDOWN.code_block_parser_cls(
            language="python",
            evaluator=writer_evaluator,
        )
        sybil = Sybil(parsers=[parser])
        document = sybil.parse(path=source_file)
        (example,) = document.examples()
        example.evaluate()

        expected_content = textwrap.dedent(
            text="""\
            ```python
            modified
            ```
            """
        )
        assert source_file.read_text(encoding="utf-8") == expected_content

    def test_encoding_parameter(self, tmp_path: Path) -> None:
        """
        Uses specified encoding when writing.
        """
        content = textwrap.dedent(
            text="""\
            ```python
            original
            ```
            """
        )
        source_file = tmp_path / "source_file.txt"
        source_file.write_text(data=content, encoding="utf-16")

        def modifying_evaluator(example: Example) -> None:
            """
            Store modified content.
            """
            example.document.namespace["modified_content"] = "modified"

        writer_evaluator = CodeBlockWriterEvaluator(
            evaluator=modifying_evaluator,
            encoding="utf-16",
        )
        parser = MARKDOWN.code_block_parser_cls(
            language="python",
            evaluator=writer_evaluator,
        )
        sybil = Sybil(parsers=[parser], encoding="utf-16")
        document = sybil.parse(path=source_file)
        (example,) = document.examples()
        example.evaluate()

        expected_content = textwrap.dedent(
            text="""\
            ```python
            modified
            ```
            """
        )
        assert source_file.read_text(encoding="utf-16") == expected_content

    def test_multiple_blocks(self, tmp_path: Path) -> None:
        """
        Handles multiple code blocks correctly.
        """
        content = textwrap.dedent(
            text="""\
            ```python
            first
            ```

            ```python
            second
            ```
            """
        )
        source_file = tmp_path / "source_file.txt"
        source_file.write_text(data=content, encoding="utf-8")

        call_count = 0

        def modifying_evaluator(example: Example) -> None:
            """
            Store modified content with incrementing value.
            """
            nonlocal call_count
            call_count += 1
            example.document.namespace["modified_content"] = (
                f"modified_{call_count}"
            )

        writer_evaluator = CodeBlockWriterEvaluator(
            evaluator=modifying_evaluator
        )
        parser = MARKDOWN.code_block_parser_cls(
            language="python",
            evaluator=writer_evaluator,
        )
        sybil = Sybil(parsers=[parser])
        document = sybil.parse(path=source_file)

        for example in document.examples():
            example.evaluate()

        expected_content = textwrap.dedent(
            text="""\
            ```python
            modified_1
            ```

            ```python
            modified_2
            ```
            """
        )
        assert source_file.read_text(encoding="utf-8") == expected_content
