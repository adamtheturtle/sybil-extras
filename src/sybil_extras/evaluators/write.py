"""
An evaluator for writing changes to a document.
"""

import textwrap
from pathlib import Path

from beartype import beartype
from sybil.example import Example


@beartype
def _get_indentation(example: Example) -> str:
    """
    Get the indentation of the parsed code in the example.
    """
    first_line = str(object=example.parsed).split(sep="\n", maxsplit=1)[0]
    region_text = example.document.text[
        example.region.start : example.region.end
    ]
    region_lines = region_text.splitlines()
    region_lines_matching_first_line = [
        line for line in region_lines if line.lstrip() == first_line.lstrip()
    ]
    try:
        first_region_line_matching_first_line = (
            region_lines_matching_first_line[0]
        )
    except IndexError:
        # Empty example
        return ""

    left_padding_region_line = len(
        first_region_line_matching_first_line
    ) - len(first_region_line_matching_first_line.lstrip())
    left_padding_parsed_line = len(first_line) - len(first_line.lstrip())
    indentation_length = left_padding_region_line - left_padding_parsed_line
    indentation_character = first_region_line_matching_first_line[0]
    return indentation_character * indentation_length


@beartype
def _count_leading_newlines(s: str) -> int:
    """Count the number of leading newlines in a string.

    Args:
        s: The input string.

    Returns:
        The number of leading newlines.
    """
    count = 0
    non_newline_found = False
    for char in s:
        if char == "\n" and not non_newline_found:
            count += 1
        else:
            non_newline_found = True
    return count


@beartype
def _lstrip_newlines(input_string: str, number_of_newlines: int) -> str:
    """Removes a specified number of newlines from the start of the string.

    Args:
        input_string: The input string to process.
        number_of_newlines: The number of newlines to remove from the
            start.

    Returns:
        The string with the specified number of leading newlines removed.
        If fewer newlines exist, removes all of them.
    """
    num_leading_newlines = _count_leading_newlines(s=input_string)
    lines_to_remove = min(num_leading_newlines, number_of_newlines)
    return input_string[lines_to_remove:]


@beartype
def _document_content_with_example_content_replaced(
    *,
    example: Example,
    existing_file_content: str,
    strip_leading_newlines: bool,
) -> str:
    """
    Get the document content with the example content replaced.
    """
    indent_prefix = _get_indentation(example=example)
    unindented_new_example_content = str(object=example.parsed.text)
    new_example_content = textwrap.indent(
        text=unindented_new_example_content,
        prefix=indent_prefix,
    )

    # Examples are given with no leading newline.
    # While it is possible that a formatter added leading newlines,
    # we assume that this is not the case, and we remove any leading
    # newlines from the replacement which were added by the padding.
    if strip_leading_newlines:
        new_example_content = _lstrip_newlines(
            input_string=new_example_content,
            number_of_newlines=example.line + example.parsed.line_offset,
        )

    indented_existing_region_content = textwrap.indent(
        text=example.region.parsed,
        prefix=indent_prefix,
    )

    document_start = existing_file_content[: example.region.start]
    document_without_start = existing_file_content[example.region.start :]

    document_with_replacement_and_no_start = document_without_start.replace(
        indented_existing_region_content.rstrip("\n"),
        new_example_content,
        count=1,
    )

    return document_start + document_with_replacement_and_no_start


@beartype
class WriteCodeBlockEvaluator:
    """
    Write the example text back into the code block in the document.
    """

    def __init__(self, *, strip_leading_newlines: bool, encoding: str) -> None:
        """
        Initialize the evaluator.
        """
        self._strip_leading_newlines = strip_leading_newlines
        self._encoding = encoding

    def __call__(self, example: Example) -> None:
        """
        Write the example text back to the document.
        """
        modified_content = _document_content_with_example_content_replaced(
            example=example,
            existing_file_content=example.document.text,
            strip_leading_newlines=self._strip_leading_newlines,
        )
        if example.document.text != modified_content:
            example.document.text = modified_content
            # We avoid writing to the file if the content is the same.
            # This is because writing to the file will update the file's
            # modification time, which can cause unnecessary rebuilds, and
            # we have seen that confuse the Git index.
            Path(example.path).write_text(
                data=modified_content,
                encoding=self._encoding,
            )
