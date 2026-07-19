"""Utilities for writing modified content back to code blocks in source
documents.

This module provides functions to update code block content in
documentation files while preserving the surrounding markup structure.
It supports multiple markup formats including Markdown, MyST, Norg, and
reStructuredText.
"""

import re
import textwrap
import threading
from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

from beartype import beartype
from sybil import Document, Example, Lexeme
from sybil.typing import Evaluator


@dataclass
class _CapturedValue:
    """A namespace value isolated to one evaluator call."""

    value: object | None = None


class _WriterLocal(threading.local):
    """Per-thread stack of namespace captures."""

    def __init__(self) -> None:
        """Initialize an empty capture stack for the current thread."""
        self.captures: dict[str, list[_CapturedValue]] = {}


class _WriterNamespace(dict[str, object]):
    """A document namespace with isolated writer result slots."""

    def __init__(self, *, namespace: dict[str, object]) -> None:
        """Initialize from an existing document namespace."""
        super().__init__(namespace)
        self._local = _WriterLocal()
        self._capture_lock = threading.Lock()
        self.write_lock = threading.RLock()

    def _active_capture(self, *, key: str) -> _CapturedValue | None:
        """Return this thread's innermost capture for ``key``."""
        captures = self._local.captures.get(key, ())
        return captures[-1] if captures else None

    @contextmanager
    def capture(self, *, key: str) -> Generator[_CapturedValue]:
        """Capture writes to ``key`` in the current thread."""
        with self._capture_lock:
            captured = _CapturedValue(value=super().pop(key, None))
        captures = self._local.captures.setdefault(key, [])
        captures.append(captured)
        try:
            yield captured
        finally:
            captures.pop()

    def __setitem__(self, key: str, value: object) -> None:
        """Store captured writer content separately for each thread."""
        capture = self._active_capture(key=key)
        if capture is None:
            super().__setitem__(key, value)
            return
        capture.value = value


_NAMESPACE_INSTALL_LOCK = threading.Lock()


@beartype
def _writer_namespace(*, document: Document) -> _WriterNamespace:
    """Return the shared writer-aware namespace for ``document``."""
    with _NAMESPACE_INSTALL_LOCK:
        namespace = document.namespace
        if not isinstance(namespace, _WriterNamespace):
            namespace = _WriterNamespace(namespace=namespace)
            document.namespace = namespace
        return namespace


@beartype
def _get_container_prefix(*, region_text: str) -> str:
    """Get a fenced block's indentation and block quote prefix."""
    fence_pattern = re.compile(
        pattern=r"^(?P<prefix>[ \t]*(?:>[ \t]*)*)(?P<fence>`{3,})",
        flags=re.MULTILINE,
    )
    fence_match = fence_pattern.match(string=region_text)
    return fence_match.group("prefix") if fence_match else ""


@beartype
def _get_source_newline(*, path: Path, encoding: str | None) -> str | None:
    """Return the first newline convention used by a source file."""
    with path.open(mode="r", encoding=encoding, newline="") as source_file:
        source_text = source_file.read()

    newline_match = re.search(pattern=r"\r\n|\r|\n", string=source_text)
    return newline_match.group() if newline_match else None


@beartype
def _get_within_code_block_indentation_prefix(example: Example) -> str:
    """Get the indentation of the parsed code in the example."""
    first_line = str(object=example.parsed).split(sep="\n", maxsplit=1)[0]
    region_text = example.document.text[
        example.region.start : example.region.end
    ]

    container_prefix = _get_container_prefix(
        region_text=region_text,
    )

    region_lines = region_text.splitlines()
    region_lines_matching_first_line = [
        line
        for line in region_lines
        if line.removeprefix(container_prefix).lstrip() == first_line.lstrip()
    ]
    first_region_line_matching_first_line = region_lines_matching_first_line[0]

    # After removing the container prefix, calculate any additional indentation
    line_without_container = (
        first_region_line_matching_first_line.removeprefix(container_prefix)
    )
    left_padding_region_line = len(line_without_container) - len(
        line_without_container.lstrip()
    )
    left_padding_parsed_line = len(first_line) - len(first_line.lstrip())
    additional_indentation_length = (
        left_padding_region_line - left_padding_parsed_line
    )

    # Build the full prefix: container prefix + additional indentation
    if additional_indentation_length > 0 and line_without_container:
        additional_indentation = line_without_container[
            :additional_indentation_length
        ]
    else:
        additional_indentation = ""

    return container_prefix + additional_indentation


@beartype
@dataclass(frozen=True, kw_only=True)
class _RegionEdit:
    """How to splice new content into a code block region.

    The writer locates ``replace_old_not_indented`` (after indenting it by
    ``within_code_block_indent_prefix``) within the region, and replaces it
    with the new content -- also indented by that prefix -- preceded by
    ``replace_new_prefix``.
    """

    within_code_block_indent_prefix: str
    replace_old_not_indented: str
    replace_new_prefix: str


@beartype
def _source_offset(*, example: Example) -> int:
    """Return where the code content starts within the example's region.

    Sybil records this on the ``source`` lexeme -- which is
    ``example.parsed`` for a code block -- as :attr:`sybil.Lexeme.offset`,
    the character position of the content relative to the region start.
    Every markup language populates it, including the stock Sybil parsers,
    so the writer can locate a block's delimiters without knowing which
    language produced the region.
    """
    parsed = example.parsed
    assert isinstance(parsed, Lexeme)  # noqa: S101
    return parsed.offset


@beartype
def _empty_block_region_edit(
    *,
    original_region_text: str,
    code_block_indent_prefix: str,
    source_offset: int,
) -> _RegionEdit:
    """Describe how to insert content into an *empty* code block.

    An empty block has no parsed content to locate and replace, so the new
    content is inserted where that content would have started: the position
    Sybil records as ``source_offset``. The text after that offset is the
    block's closing delimiter, and whether it exists tells us how the block
    is shaped -- without having to recognize any particular markup language:

    * A non-empty closing delimiter (a fenced block's closing backtick or
      tilde line, the Norg ``@end`` tag, ...) sits on its own line after the
      content, so the content goes at the block's own indentation, just
      before that line.
    * No closing delimiter means an indented literal block (as in
      reStructuredText), whose content is an indented sub-block separated
      from the opening line by a blank line.
    """
    closing_delimiter = original_region_text[source_offset:]
    has_closing_delimiter = bool(closing_delimiter.strip())

    if has_closing_delimiter:
        container_prefix = _get_container_prefix(
            region_text=original_region_text,
        )
        return _RegionEdit(
            within_code_block_indent_prefix=(
                container_prefix or code_block_indent_prefix
            ),
            replace_old_not_indented="\n",
            replace_new_prefix="\n",
        )

    return _RegionEdit(
        within_code_block_indent_prefix=code_block_indent_prefix + "   ",
        replace_old_not_indented="\n",
        replace_new_prefix="\n\n",
    )


@beartype
def _get_modified_region_text(
    *,
    example: Example,
    original_region_text: str,
    new_code_block_content: str,
) -> str:
    """
    Get the region text to use after the example content is
    replaced.
    """
    first_line = original_region_text.split(maxsplit=1, sep="\n")[0]
    code_block_indent_prefix = first_line[
        : len(first_line) - len(first_line.lstrip())
    ]

    if example.parsed:
        edit = _RegionEdit(
            within_code_block_indent_prefix=(
                _get_within_code_block_indentation_prefix(example=example)
            ),
            replace_old_not_indented=example.parsed,
            replace_new_prefix="",
        )
        search_region_text = original_region_text
    else:
        source_offset = _source_offset(example=example)
        edit = _empty_block_region_edit(
            original_region_text=original_region_text,
            code_block_indent_prefix=code_block_indent_prefix,
            source_offset=source_offset,
        )
        search_region_text = original_region_text[:source_offset]

    indented_example_parsed = textwrap.indent(
        text=edit.replace_old_not_indented,
        prefix=edit.within_code_block_indent_prefix,
    )
    replacement_text = textwrap.indent(
        text=new_code_block_content,
        prefix=edit.within_code_block_indent_prefix,
    )

    if not replacement_text.endswith("\n"):
        replacement_text += "\n"

    text_to_replace_index = search_region_text.rfind(indented_example_parsed)
    if text_to_replace_index < 0:
        msg = (
            "Parsed code is not contiguous in its source region; "
            "grouped examples cannot be written"
        )
        raise ValueError(msg)
    text_before_replacement = original_region_text[:text_to_replace_index]
    text_after_replacement = original_region_text[
        text_to_replace_index + len(indented_example_parsed) :
    ]
    region_with_replaced_text = (
        text_before_replacement
        + edit.replace_new_prefix
        + replacement_text
        + text_after_replacement
    )
    stripped_of_newlines_region = region_with_replaced_text.rstrip("\n")
    # Keep the same number of newlines at the end of the region.
    num_newlines_at_end = len(original_region_text) - len(
        original_region_text.rstrip("\n")
    )
    newlines_at_end = "\n" * num_newlines_at_end
    return stripped_of_newlines_region + newlines_at_end


@beartype
def _overwrite_example_content(
    *,
    example: Example,
    new_content: str,
    encoding: str | None = None,
) -> None:
    """Update the source document and file with modified example content.

    This updates both the in-memory document and writes changes to disk.
    It also adjusts the positions of subsequent regions in the document.

    Args:
        example: The Sybil example whose content should be replaced.
        new_content: The new content to write into the code block.
        encoding: The encoding to use when writing the file. If ``None``,
            use the system default.
    """
    original_region_text = example.document.text[
        example.region.start : example.region.end
    ]
    modified_region_text = _get_modified_region_text(
        original_region_text=original_region_text,
        example=example,
        new_code_block_content=new_content,
    )

    if modified_region_text != original_region_text:
        path = Path(example.path)
        source_newline = _get_source_newline(path=path, encoding=encoding)
        existing_file_content = example.document.text
        modified_document_content = (
            existing_file_content[: example.region.start]
            + modified_region_text
            + existing_file_content[example.region.end :]
        )
        example.document.text = modified_document_content
        offset = len(modified_region_text) - len(original_region_text)
        subsequent_regions = [
            region
            for _, region in example.document.regions
            if region.start >= example.region.end
        ]
        for region in subsequent_regions:
            region.start += offset
            region.end += offset
        path.write_text(
            data=modified_document_content,
            encoding=encoding,
            newline=source_newline,
        )


@beartype
class CodeBlockWriterEvaluator:
    """An evaluator wrapper that writes modified content back to code
    blocks.

    This evaluator wraps another evaluator and writes any modifications
    made to the example content back to the source document. It is useful
    for building evaluators that transform code blocks, such as formatters
    or auto-fixers.

    The wrapped evaluator should store the modified content in
    ``example.document.namespace[namespace_key]`` for it to be written back.
    """

    def __init__(
        self,
        *,
        evaluator: Evaluator,
        namespace_key: str = "modified_content",
        encoding: str | None = None,
    ) -> None:
        """Initialize the evaluator.

        Args:
            evaluator: The evaluator to wrap. This evaluator should store
                modified content in
                ``example.document.namespace[namespace_key]`` if changes
                should be written back.
            namespace_key: The key in ``example.document.namespace`` where the
                wrapped evaluator stores modified content.
            encoding: The encoding to use when writing files. If ``None``,
                use the system default.
        """
        self._evaluator = evaluator
        self._namespace_key = namespace_key
        self._encoding = encoding

    def __call__(self, example: Example) -> str | None:
        """Run the wrapped evaluator and write any modifications back.

        If the wrapped evaluator raises an exception, modifications are
        still written before the exception is re-raised. This ensures
        that formatters or auto-fixers can update files even when other
        checks (like linter checks) fail.
        """
        namespace = _writer_namespace(document=example.document)
        with namespace.capture(key=self._namespace_key) as captured:
            try:
                result = self._evaluator(example)
            finally:
                modified_content = captured.value
                if modified_content is not None and not isinstance(
                    modified_content, str
                ):
                    msg = "Modified code block content must be a string"
                    raise TypeError(msg)
                if (
                    modified_content is not None
                    and modified_content != example.parsed
                ):
                    with namespace.write_lock:
                        _overwrite_example_content(
                            example=example,
                            new_content=modified_content,
                            encoding=self._encoding,
                        )
        return result
