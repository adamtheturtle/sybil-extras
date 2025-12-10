"""Utilities for writing modified content back to code blocks in source
documents.

This module provides functions to update code block content in
documentation files while preserving the surrounding markup structure.
It supports multiple markup formats including Markdown, MyST, Norg, and
reStructuredText.
"""

import re
import textwrap
from pathlib import Path

from beartype import beartype
from sybil import Example
from sybil.typing import Evaluator


@beartype
def _get_within_code_block_indentation_prefix(example: Example) -> str:
    """
    Get the indentation of the parsed code in the example.
    """
    first_line = str(object=example.parsed).split(sep="\n", maxsplit=1)[0]
    region_text = example.document.text[
        example.region.start : example.region.end
    ]

    # Extract blockquote/container prefix from the region text
    # This handles Djot/Markdown blockquotes (lines starting with "> ")
    fence_pattern = re.compile(
        pattern=r"^(?P<prefix>[ \t]*(?:>[ \t]*)*)(?P<fence>`{3,})",
        flags=re.MULTILINE,
    )
    fence_match = fence_pattern.match(string=region_text)
    container_prefix = fence_match.group("prefix") if fence_match else ""

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
        indentation_character = line_without_container[0]
        additional_indentation = (
            indentation_character * additional_indentation_length
        )
    else:
        additional_indentation = ""

    return container_prefix + additional_indentation


@beartype
def _get_modified_region_text(
    example: Example,
    original_region_text: str,
    new_code_block_content: str,
) -> str:
    """
    Get the region text to use after the example content is replaced.
    """
    first_line = original_region_text.split(sep="\n")[0]
    code_block_indent_prefix = first_line[
        : len(first_line) - len(first_line.lstrip())
    ]

    if example.parsed:
        within_code_block_indent_prefix = (
            _get_within_code_block_indentation_prefix(example=example)
        )
        replace_old_not_indented = example.parsed
        replace_new_prefix = ""
    # This is a break of the abstraction, - we really should not have
    # to know about markup language specifics here.
    elif original_region_text.endswith("```"):
        # Markdown or MyST
        within_code_block_indent_prefix = code_block_indent_prefix
        replace_old_not_indented = "\n"
        replace_new_prefix = "\n"
    elif original_region_text.rstrip().endswith("@end"):
        # Norg
        within_code_block_indent_prefix = code_block_indent_prefix
        replace_old_not_indented = "\n"
        replace_new_prefix = "\n"
    else:
        # reStructuredText
        within_code_block_indent_prefix = code_block_indent_prefix + "   "
        replace_old_not_indented = "\n"
        replace_new_prefix = "\n\n"

    indented_example_parsed = textwrap.indent(
        text=replace_old_not_indented,
        prefix=within_code_block_indent_prefix,
    )
    replacement_text = textwrap.indent(
        text=new_code_block_content,
        prefix=within_code_block_indent_prefix,
    )

    if not replacement_text.endswith("\n"):
        replacement_text += "\n"

    text_to_replace_index = original_region_text.rfind(indented_example_parsed)
    text_before_replacement = original_region_text[:text_to_replace_index]
    text_after_replacement = original_region_text[
        text_to_replace_index + len(indented_example_parsed) :
    ]
    region_with_replaced_text = (
        text_before_replacement
        + replace_new_prefix
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
        Path(example.path).write_text(
            data=modified_document_content,
            encoding=encoding,
        )


@beartype
class CodeBlockWriterEvaluator:
    """An evaluator wrapper that writes modified content back to code blocks.

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

    def __call__(self, example: Example) -> None:
        """Run the wrapped evaluator and write any modifications back.

        If the wrapped evaluator raises an exception, modifications are
        still written before the exception is re-raised. This ensures
        that formatters or auto-fixers can update files even when other
        checks (like linter checks) fail.
        """
        try:
            self._evaluator(example)
        finally:
            modified_content = example.document.namespace.get(
                self._namespace_key
            )
            if modified_content is not None:
                # Clear the namespace key to prevent stale data affecting
                # subsequent examples.
                del example.document.namespace[self._namespace_key]
                if modified_content != example.parsed:
                    _overwrite_example_content(
                        example=example,
                        new_content=modified_content,
                        encoding=self._encoding,
                    )
