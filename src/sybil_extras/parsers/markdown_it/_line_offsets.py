"""
Line offset calculation for the markdown_it parsers.
"""

from beartype import beartype


@beartype
def line_offsets(*, text: str) -> list[int]:
    """Return the character offset of each line in the text.

    The returned list has one entry per line, where entry[i] is the
    character position where line i starts.
    """
    offsets = [0]
    for i, char in enumerate(iterable=text):
        if char == "\n":
            offsets.append(i + 1)
    return offsets
