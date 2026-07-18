"""Tests for the code_block_writer module."""

import textwrap
import threading
from pathlib import Path

import pytest
from sybil import Example, Sybil
from sybil.example import SybilFailure

from sybil_extras.evaluators.code_block_writer import CodeBlockWriterEvaluator
from sybil_extras.evaluators.no_op import NoOpEvaluator
from sybil_extras.languages import (
    DJOT,
    MARKDOWN,
    MARKDOWN_IT,
    MDX,
    MYST,
    MYST_PARSER,
    NORG,
    RESTRUCTUREDTEXT,
    MarkupLanguage,
)
from sybil_extras.parsers.markdown.group_all import GroupAllParser


def test_write_back_of_group_spanning_multiple_blocks_is_rejected(
    tmp_path: Path,
) -> None:
    """Writing back a group made of separate code blocks is rejected.

    ``GroupAllParser`` combines several code blocks into one example whose
    parsed source is the concatenation of every block's code.  In the
    document those blocks are separated by fences and blank lines, so the
    combined code never appears as one contiguous run of text in the
    source.  There is therefore nowhere to slice the replacement in, and
    attempting to write it back would corrupt the file.  The writer raises
    instead, and the file is left unchanged.
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
    source_file = tmp_path / "source_file.md"
    source_file.write_text(data=content, encoding="utf-8")

    def modifying_evaluator(example: Example) -> None:
        """Uppercase the grouped source."""
        example.document.namespace["modified_content"] = str(
            object=example.parsed
        ).upper()

    writer_evaluator = CodeBlockWriterEvaluator(evaluator=modifying_evaluator)
    document = Sybil(
        parsers=[
            MARKDOWN.code_block_parser_cls(
                language="python",
                evaluator=NoOpEvaluator(),
            ),
            GroupAllParser(evaluator=writer_evaluator, pad_groups=False),
        ]
    ).parse(path=source_file)

    examples = list(document.examples())
    for example in examples[:-1]:
        example.evaluate()

    with pytest.raises(
        expected_exception=ValueError,
        match="grouped examples cannot be written",
    ):
        examples[-1].evaluate()

    assert source_file.read_text(encoding="utf-8") == content


def test_concurrent_writes_keep_each_edit(tmp_path: Path) -> None:
    """Concurrent evaluations retain both code block edits."""
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
    source_file = tmp_path / "source_file.md"
    source_file.write_text(data=content, encoding="utf-8")
    first_ready = threading.Event()
    release_first = threading.Event()

    def modifying_evaluator(example: Example) -> None:
        """Uppercase the block after arranging an overlapping call."""
        source = str(object=example.parsed)
        example.document.namespace["modified_content"] = source.upper()
        if source.strip() == "first":
            first_ready.set()
            assert release_first.wait(timeout=5)

    writer_evaluator = CodeBlockWriterEvaluator(evaluator=modifying_evaluator)
    parser = MARKDOWN.code_block_parser_cls(
        language="python",
        evaluator=writer_evaluator,
    )
    document = Sybil(parsers=[parser]).parse(path=source_file)
    first, second = document.examples()
    first_thread = threading.Thread(target=first.evaluate)

    first_thread.start()
    assert first_ready.wait(timeout=5)
    second.evaluate()
    release_first.set()
    first_thread.join(timeout=5)

    assert not first_thread.is_alive()
    expected = content.replace("first", "FIRST").replace("second", "SECOND")
    assert source_file.read_text(encoding="utf-8") == expected
    document.namespace["ordinary"] = "shared"
    assert document.namespace["ordinary"] == "shared"


def test_non_string_modified_content_raises(tmp_path: Path) -> None:
    """Modified code block content must remain a string."""
    source_file = tmp_path / "source_file.md"
    source_file.write_text(data="```python\noriginal\n```\n", encoding="utf-8")

    def modifying_evaluator(example: Example) -> None:
        """Store an invalid modified content value."""
        example.document.namespace["modified_content"] = 1

    writer_evaluator = CodeBlockWriterEvaluator(evaluator=modifying_evaluator)
    parser = MARKDOWN.code_block_parser_cls(
        language="python",
        evaluator=writer_evaluator,
    )
    (example,) = Sybil(parsers=[parser]).parse(path=source_file).examples()

    with pytest.raises(expected_exception=TypeError, match="must be a string"):
        example.evaluate()


def test_writes_modified_content(
    *,
    tmp_path: Path,
    markup_language: MarkupLanguage,
) -> None:
    """Writes modified content from namespace to source file."""
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
    rst_content = textwrap.dedent(
        text="""\
        Not in code block

        .. code-block:: python

            original
        """
    )
    original_content = {
        RESTRUCTUREDTEXT: rst_content,
        MARKDOWN: markdown_content,
        MARKDOWN_IT: markdown_content,
        MDX: markdown_content,
        DJOT: markdown_content,
        NORG: norg_content,
        MYST: myst_content,
        MYST_PARSER: markdown_content,
    }[markup_language]

    source_file = tmp_path / "source_file.txt"
    source_file.write_text(data=original_content, encoding="utf-8")

    def modifying_evaluator(example: Example) -> None:
        """Store modified content in namespace."""
        example.document.namespace["modified_content"] = "modified"

    writer_evaluator = CodeBlockWriterEvaluator(evaluator=modifying_evaluator)
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
    rst_expected = textwrap.dedent(
        text="""\
        Not in code block

        .. code-block:: python

            modified
        """
    )
    expected_content = {
        RESTRUCTUREDTEXT: rst_expected,
        MARKDOWN: markdown_expected,
        MARKDOWN_IT: markdown_expected,
        MDX: markdown_expected,
        DJOT: markdown_expected,
        NORG: norg_expected,
        MYST: myst_expected,
        MYST_PARSER: markdown_expected,
    }[markup_language]

    assert source_file.read_text(encoding="utf-8") == expected_content


def test_writes_on_evaluator_exception(tmp_path: Path) -> None:
    """When the wrapped evaluator raises an exception, modifications are
    still
    written to the file before the exception is re-raised.

    This is important for formatters that should update files even when
    subsequent checks fail.
    """
    original_content = textwrap.dedent(
        text="""\
        ```python
        original
        ```
        """
    )
    source_file = tmp_path / "source_file.md"
    source_file.write_text(data=original_content, encoding="utf-8")

    class FailingEvaluator:
        """An evaluator that modifies content then raises an exception."""

        def __init__(self, namespace_key: str) -> None:
            """Initialize the evaluator with a namespace key."""
            self._namespace_key = namespace_key

        def __call__(self, example: Example) -> None:
            """Modify content then raise an exception."""
            example.document.namespace[self._namespace_key] = "modified"
            msg = "Intentional failure"
            raise RuntimeError(msg)

    namespace_key = "modified_content"
    failing_evaluator = FailingEvaluator(namespace_key=namespace_key)
    writer_evaluator = CodeBlockWriterEvaluator(
        evaluator=failing_evaluator,
        namespace_key=namespace_key,
    )

    parser = MARKDOWN.code_block_parser_cls(
        language="python",
        evaluator=writer_evaluator,
    )
    sybil = Sybil(parsers=[parser])

    document = sybil.parse(path=source_file)
    (example,) = document.examples()

    with pytest.raises(expected_exception=RuntimeError, match="Intentional"):
        example.evaluate()

    # Despite the error, the file should have been updated
    updated_content = source_file.read_text(encoding="utf-8")
    assert updated_content != original_content
    assert "modified" in updated_content


def test_returns_wrapped_evaluator_failure(tmp_path: Path) -> None:
    """A textual failure from the wrapped evaluator is returned to
    Sybil.
    """
    source_file = tmp_path / "source_file.md"
    source_file.write_text(
        data="```python\npass\n```\n",
        encoding="utf-8",
    )

    def failing_evaluator(example: Example) -> str:
        """Return a textual failure without modifying the example."""
        del example
        return "formatter reported a failure"

    writer_evaluator = CodeBlockWriterEvaluator(evaluator=failing_evaluator)
    parser = MARKDOWN.code_block_parser_cls(
        language="python",
        evaluator=writer_evaluator,
    )
    document = Sybil(parsers=[parser]).parse(path=source_file)
    (example,) = document.examples()

    assert writer_evaluator(example) == "formatter reported a failure"
    with pytest.raises(
        expected_exception=SybilFailure,
        match="formatter reported a failure",
    ):
        example.evaluate()


def test_empty_code_block_write_content(
    *,
    tmp_path: Path,
    markup_language: MarkupLanguage,
) -> None:
    """Content can be written to an empty code block."""
    rst_content = textwrap.dedent(
        text="""\
        Not in code block

        .. code-block:: python

        After empty code block
        """,
    )
    markdown_content = textwrap.dedent(
        text="""\
        Not in code block

        ```python
        ```

        After empty code block
        """,
    )

    myst_content = textwrap.dedent(
        text="""\
        Not in code block

        ```{code} python
        ```

        After empty code block
        """,
    )

    norg_content = textwrap.dedent(
        text="""\
        Not in code block

        @code python
        @end

        After empty code block
        """,
    )

    content = {
        RESTRUCTUREDTEXT: rst_content,
        MARKDOWN: markdown_content,
        MARKDOWN_IT: markdown_content,
        MDX: markdown_content,
        DJOT: markdown_content,
        NORG: norg_content,
        MYST: myst_content,
        MYST_PARSER: markdown_content,
    }[markup_language]
    source_file = tmp_path / "source_file.txt"
    source_file.write_text(data=content, encoding="utf-8")

    def modifying_evaluator(example: Example) -> None:
        """Store modified content in namespace."""
        # Add multiple newlines to show that they are not included in the file.
        # No code block in reStructuredText ends with multiple newlines.
        example.document.namespace["modified_content"] = "foobar\n\n"

    writer_evaluator = CodeBlockWriterEvaluator(evaluator=modifying_evaluator)
    parser = markup_language.code_block_parser_cls(
        language="python",
        evaluator=writer_evaluator,
    )
    sybil = Sybil(parsers=[parser])

    document = sybil.parse(path=source_file)
    (example,) = document.examples()

    markdown_expected = textwrap.dedent(
        text="""\
        Not in code block

        ```python
        foobar

        ```

        After empty code block
        """
    )
    myst_expected = textwrap.dedent(
        text="""\
        Not in code block

        ```{code} python
        foobar

        ```

        After empty code block
        """
    )
    norg_expected = textwrap.dedent(
        text="""\
        Not in code block

        @code python
        foobar

        @end

        After empty code block
        """
    )
    # There is no code block in reStructuredText that ends with multiple
    # newlines.
    rst_expected = textwrap.dedent(
        text="""\
        Not in code block

        .. code-block:: python

           foobar

        After empty code block
        """
    )
    expected_content = {
        RESTRUCTUREDTEXT: rst_expected,
        MARKDOWN: markdown_expected,
        MARKDOWN_IT: markdown_expected,
        MDX: markdown_expected,
        DJOT: markdown_expected,
        NORG: norg_expected,
        MYST: myst_expected,
        MYST_PARSER: markdown_expected,
    }[markup_language]

    example.evaluate()
    assert source_file.read_text(encoding="utf-8") == expected_content


def test_empty_tilde_fenced_block(tmp_path: Path) -> None:
    """Content is inserted without indentation inside a tilde fence."""
    source_file = tmp_path / "source_file.md"
    source_file.write_text(data="~~~python\n~~~\n", encoding="utf-8")

    def modifying_evaluator(example: Example) -> None:
        """Store modified content in the namespace."""
        example.document.namespace["modified_content"] = "inserted"

    writer_evaluator = CodeBlockWriterEvaluator(evaluator=modifying_evaluator)
    parser = MARKDOWN_IT.code_block_parser_cls(
        language="python",
        evaluator=writer_evaluator,
    )
    document = Sybil(parsers=[parser]).parse(path=source_file)
    (example,) = document.examples()

    example.evaluate()

    assert source_file.read_text(encoding="utf-8") == (
        "~~~python\ninserted\n~~~\n"
    )


def test_empty_code_block_with_options(
    *,
    tmp_path: Path,
    markup_language: MarkupLanguage,
) -> None:
    """
    It is possible to write content to an empty code block even if that
    code
    block has options.
    """
    if markup_language in (MARKDOWN, MARKDOWN_IT, MYST_PARSER, DJOT, NORG):
        # Markdown-like formats do not support code block options.
        return

    rst_content = textwrap.dedent(
        text="""\
        Not in code block

        .. code-block:: python
           :emphasize-lines: 2,3

        After empty code block
        """,
    )

    myst_content = textwrap.dedent(
        text="""\
        Not in code block

        ```{code} python
        :emphasize-lines: 2,3
        ```

        After empty code block
        """,
    )

    mdx_content = textwrap.dedent(
        text="""\
        Not in code block

        ```python title="example.py"
        ```

        After empty code block
        """,
    )

    content = {
        RESTRUCTUREDTEXT: rst_content,
        MYST: myst_content,
        MDX: mdx_content,
    }[markup_language]
    source_file = tmp_path / "source_file.txt"
    source_file.write_text(data=content, encoding="utf-8")

    def modifying_evaluator(example: Example) -> None:
        """Store modified content in namespace."""
        example.document.namespace["modified_content"] = "foobar"

    writer_evaluator = CodeBlockWriterEvaluator(evaluator=modifying_evaluator)
    parser = markup_language.code_block_parser_cls(
        language="python",
        evaluator=writer_evaluator,
    )
    sybil = Sybil(parsers=[parser])

    document = sybil.parse(path=source_file)
    (example,) = document.examples()

    myst_expected = textwrap.dedent(
        text="""\
        Not in code block

        ```{code} python
        :emphasize-lines: 2,3
        foobar
        ```

        After empty code block
        """
    )
    rst_expected = textwrap.dedent(
        text="""\
        Not in code block

        .. code-block:: python
           :emphasize-lines: 2,3

           foobar

        After empty code block
        """
    )
    expected_content = {
        RESTRUCTUREDTEXT: rst_expected,
        MYST: myst_expected,
        MDX: textwrap.dedent(
            text="""\
            Not in code block

            ```python title="example.py"
            foobar
            ```

            After empty code block
            """
        ),
    }[markup_language]

    example.evaluate()
    assert source_file.read_text(encoding="utf-8") == expected_content


@pytest.mark.parametrize(
    argnames="new_content",
    argvalues=(
        "",
        # Code blocks in reStructuredText cannot contain just newlines.
        # Therefore we treat this as an empty code block.
        "\n\n",
    ),
)
def test_empty_code_block_write_empty(
    *,
    tmp_path: Path,
    new_content: str,
) -> None:
    """
    No error is given when trying to write empty content to an empty
    code
    block.
    """
    content = textwrap.dedent(
        text="""\
        Not in code block

        .. code-block:: python

        After empty code block
        """
    )
    source_file = tmp_path / "source_file.txt"
    source_file.write_text(data=content, encoding="utf-8")

    def modifying_evaluator(example: Example) -> None:
        """Store modified content in namespace."""
        example.document.namespace["modified_content"] = new_content

    writer_evaluator = CodeBlockWriterEvaluator(evaluator=modifying_evaluator)
    parser = RESTRUCTUREDTEXT.code_block_parser_cls(
        language="python",
        evaluator=writer_evaluator,
    )
    sybil = Sybil(parsers=[parser])

    document = sybil.parse(path=source_file)
    (example,) = document.examples()
    example.evaluate()
    assert source_file.read_text(encoding="utf-8") == content


def test_djot_quoted_code_block(tmp_path: Path) -> None:
    """Changes are written to a Djot code block inside a block quote.

    Djot supports two types of code blocks in block quotes:
    1. With explicit closing fence (```): Standard fenced code block
    2. Without closing fence: Code block implicitly closed by container end

    Once https://github.com/simplistix/sybil/issues/160 is done, we can expand
    this test to cover Markdown / MDX / MyST.
    """
    original_content = textwrap.dedent(
        text="""\
        Some text before

        > ```python
        > x = 2 + 2
        > assert x == 4
        > ```

        Text between blocks

        > ```python
        > a = 1 + 1
        > assert a == 2

        Text after
        """
    )
    djot_file = tmp_path / "test_document.example.djot"
    djot_file.write_text(data=original_content, encoding="utf-8")

    def modifying_evaluator(example: Example) -> None:
        """Store modified content in namespace."""
        example.document.namespace["modified_content"] = "y = 5"

    writer_evaluator = CodeBlockWriterEvaluator(evaluator=modifying_evaluator)
    parser = DJOT.code_block_parser_cls(
        language="python",
        evaluator=writer_evaluator,
    )
    sybil = Sybil(parsers=[parser])
    document = sybil.parse(path=djot_file)
    (first_example, second_example) = document.examples()
    first_example.evaluate()
    second_example.evaluate()

    expected_content = textwrap.dedent(
        text="""\
        Some text before

        > ```python
        > y = 5
        > ```

        Text between blocks

        > ```python
        > y = 5

        Text after
        """
    )
    assert djot_file.read_text(encoding="utf-8") == expected_content
    # Namespace key is cleared after write
    assert "modified_content" not in document.namespace


def test_no_write_when_content_unchanged(tmp_path: Path) -> None:
    """Does not write when modified content matches original."""
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
        """Store same content in namespace."""
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


def test_no_write_when_no_namespace_key(tmp_path: Path) -> None:
    """Does not write when namespace key is not set."""
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


def test_custom_namespace_key(tmp_path: Path) -> None:
    """Uses custom namespace key for modified content."""
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
        """Store modified content with custom key."""
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


def test_encoding_parameter(tmp_path: Path) -> None:
    """Uses specified encoding when writing."""
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
        """Store modified content."""
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


def test_indented_existing_block(
    *,
    tmp_path: Path,
    markup_language: MarkupLanguage,
) -> None:
    """Changes are written to indented code blocks."""
    if markup_language == NORG:
        # Norg does not support indented code blocks in the same way.
        return

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
    rst_original_content = textwrap.dedent(
        text="""\
        Not in code block

            .. code-block:: python

               x = 2 + 2
               assert x == 4
        """
    )
    original_content = {
        RESTRUCTUREDTEXT: rst_original_content,
        MARKDOWN: markdown_content,
        MARKDOWN_IT: markdown_content,
        MDX: markdown_content,
        DJOT: markdown_content,
        NORG: norg_content,
        MYST: myst_content,
        MYST_PARSER: markdown_content,
    }[markup_language]
    source_file = tmp_path / "source_file.txt"
    source_file.write_text(data=original_content, encoding="utf-8")

    def modifying_evaluator(example: Example) -> None:
        """Store modified content in namespace."""
        example.document.namespace["modified_content"] = "foobar"

    writer_evaluator = CodeBlockWriterEvaluator(evaluator=modifying_evaluator)
    parser = markup_language.code_block_parser_cls(
        language="python",
        evaluator=writer_evaluator,
    )
    sybil = Sybil(parsers=[parser])

    document = sybil.parse(path=source_file)
    (example,) = document.examples()
    example.evaluate()
    source_file_content = source_file.read_text(encoding="utf-8")

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
    rst_expected = textwrap.dedent(
        text="""\
        Not in code block

            .. code-block:: python

               foobar
        """
    )
    expected_content = {
        RESTRUCTUREDTEXT: rst_expected,
        MARKDOWN: markdown_expected,
        MARKDOWN_IT: markdown_expected,
        MDX: markdown_expected,
        DJOT: markdown_expected,
        NORG: norg_expected,
        MYST: myst_expected,
        MYST_PARSER: markdown_expected,
    }[markup_language]
    assert source_file_content == expected_content


def test_indented_empty_existing_block(
    *,
    tmp_path: Path,
    markup_language: MarkupLanguage,
) -> None:
    """Changes are written to indented empty code blocks."""
    if markup_language == NORG:
        # Norg does not support indented code blocks in the same way.
        return

    markdown_content = textwrap.dedent(
        text="""\
        Not in code block

                ```python
                ```

        After code block
        """
    )
    myst_content = textwrap.dedent(
        text="""\
        Not in code block

                ```{code} python
                ```

        After code block
        """
    )
    norg_content = textwrap.dedent(
        text="""\
        Not in code block

                @code python
                @end

        After code block
        """
    )
    rst_original_content = textwrap.dedent(
        text="""\
        Not in code block

                .. code-block:: python

        After code block
        """
    )
    original_content = {
        RESTRUCTUREDTEXT: rst_original_content,
        MARKDOWN: markdown_content,
        MARKDOWN_IT: markdown_content,
        MDX: markdown_content,
        DJOT: markdown_content,
        NORG: norg_content,
        MYST: myst_content,
        MYST_PARSER: markdown_content,
    }[markup_language]
    source_file = tmp_path / "source_file.txt"
    source_file.write_text(data=original_content, encoding="utf-8")

    def modifying_evaluator(example: Example) -> None:
        """Store modified content in namespace."""
        example.document.namespace["modified_content"] = "foobar"

    writer_evaluator = CodeBlockWriterEvaluator(evaluator=modifying_evaluator)
    parser = markup_language.code_block_parser_cls(
        language="python",
        evaluator=writer_evaluator,
    )
    sybil = Sybil(parsers=[parser])

    document = sybil.parse(path=source_file)
    (example,) = document.examples()
    example.evaluate()
    source_file_content = source_file.read_text(encoding="utf-8")

    markdown_expected = textwrap.dedent(
        text="""\
        Not in code block

                ```python
                foobar
                ```

        After code block
        """
    )
    myst_expected = textwrap.dedent(
        text="""\
        Not in code block

                ```{code} python
                foobar
                ```

        After code block
        """
    )
    norg_expected = textwrap.dedent(
        text="""\
        Not in code block

                @code python
                foobar
                @end

        After code block
        """
    )
    rst_expected = textwrap.dedent(
        text="""\
        Not in code block

                .. code-block:: python

                   foobar

        After code block
        """
    )
    expected_content = {
        RESTRUCTUREDTEXT: rst_expected,
        MARKDOWN: markdown_expected,
        MARKDOWN_IT: markdown_expected,
        MDX: markdown_expected,
        DJOT: markdown_expected,
        NORG: norg_expected,
        MYST: myst_expected,
        MYST_PARSER: markdown_expected,
    }[markup_language]
    assert source_file_content == expected_content


def test_multiple_blocks(tmp_path: Path) -> None:
    """Handles multiple code blocks correctly."""
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
        """Store modified content with incrementing value."""
        nonlocal call_count
        call_count += 1
        example.document.namespace["modified_content"] = (
            f"modified_{call_count}"
        )

    writer_evaluator = CodeBlockWriterEvaluator(evaluator=modifying_evaluator)
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


def test_mixed_tab_space_indentation(tmp_path: Path) -> None:
    """
    Changes are written correctly when code block indentation uses mixed
    tabs
    and spaces.
    """
    # Content with one tab followed by three spaces for indentation
    original_content = "\t.. code-block:: python\n\n\t   x = 1\n"
    source_file = tmp_path / "source_file.rst"
    source_file.write_text(data=original_content, encoding="utf-8")

    def modifying_evaluator(example: Example) -> None:
        """Store modified content in namespace."""
        example.document.namespace["modified_content"] = "y = 2"

    writer_evaluator = CodeBlockWriterEvaluator(evaluator=modifying_evaluator)
    parser = RESTRUCTUREDTEXT.code_block_parser_cls(
        language="python",
        evaluator=writer_evaluator,
    )
    sybil = Sybil(parsers=[parser])

    document = sybil.parse(path=source_file)
    (example,) = document.examples()
    example.evaluate()

    # The indentation should be preserved: one tab + three spaces
    expected_content = "\t.. code-block:: python\n\n\t   y = 2\n"
    assert source_file.read_text(encoding="utf-8") == expected_content


def test_changes_lines(tmp_path: Path) -> None:
    """If writing to a file changes the number of lines in the file, that
    does
    not affect the next code block.

    This test case is a narrow version of
    https://github.com/adamtheturtle/doccmd/issues/451.
    """
    content = textwrap.dedent(
        text="""\
        ```python
        x = 1
        x = 1
        x = 1
        x = 1
        ```

        ```python
        x = 1
        ```
        """
    )
    source_file = tmp_path / "source_file.txt"
    source_file.write_text(data=content, encoding="utf-8")

    def modifying_evaluator(example: Example) -> None:
        """Store modified content."""
        example.document.namespace["modified_content"] = "pass"

    writer_evaluator = CodeBlockWriterEvaluator(evaluator=modifying_evaluator)
    parser = MARKDOWN.code_block_parser_cls(
        language="python",
        evaluator=writer_evaluator,
    )
    sybil = Sybil(parsers=[parser])

    document = sybil.parse(path=source_file)
    (first_example, second_example) = document.examples()
    first_example.evaluate()
    second_example.evaluate()
    expected_content = textwrap.dedent(
        text="""\
        ```python
        pass
        ```

        ```python
        pass
        ```
        """
    )

    assert source_file.read_text(encoding="utf-8") == expected_content
