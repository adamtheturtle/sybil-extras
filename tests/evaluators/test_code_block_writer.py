"""
Tests for the code_block_writer module.
"""

import textwrap
from pathlib import Path

from sybil import Example, Sybil

from sybil_extras.evaluators.code_block_writer import CodeBlockWriterEvaluator
from sybil_extras.evaluators.no_op import NoOpEvaluator
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

        writer_evaluator = CodeBlockWriterEvaluator(evaluator=NoOpEvaluator())
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
