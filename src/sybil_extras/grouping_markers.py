"""Utilities for adding magic comment markers to grouped code blocks.

These markers allow tools like doccmd to edit files containing grouped
blocks by preserving the delimiters that separate individual code blocks
within a group.
"""

from collections.abc import Sequence
from dataclasses import dataclass

from beartype import beartype


@beartype
@dataclass(frozen=True)
class GroupDelimiters:
    """Delimiters for marking code block boundaries within a group.

    Attributes:
        start_template: Template for start delimiter.
            Use {block_index} placeholder for block number.
        end_template: Template for end delimiter.
            Use {block_index} placeholder for block number.
    """

    start_template: str
    end_template: str

    def get_start_marker(self, block_index: int) -> str:
        """Get the start marker for a specific block.

        Args:
            block_index: The zero-based index of the block.

        Returns:
            The formatted start marker.
        """
        return self.start_template.format(block_index=block_index)

    def get_end_marker(self, block_index: int) -> str:
        """Get the end marker for a specific block.

        Args:
            block_index: The zero-based index of the block.

        Returns:
            The formatted end marker.
        """
        return self.end_template.format(block_index=block_index)


@beartype
@dataclass(frozen=True)
class BlockPosition:
    """Position information for a code block within grouped source.

    Attributes:
        start_line: Line number where the block starts (0-based).
        end_line: Line number where the block ends (0-based, exclusive).
        block_index: The index of this block within the group.
    """

    start_line: int
    end_line: int
    block_index: int


@beartype
def get_group_delimiters(language: str) -> GroupDelimiters:
    """Get delimiter templates for a given language.

    Args:
        language: The programming language (e.g., 'python', 'javascript').

    Returns:
        GroupDelimiters with comment-based templates for the language.

    Raises:
        ValueError: If the language is not supported.
    """
    # Map language to single-line comment syntax
    comment_styles = {
        "python": "#",
        "ruby": "#",
        "bash": "#",
        "shell": "#",
        "sh": "#",
        "perl": "#",
        "r": "#",
        "yaml": "#",
        "dockerfile": "#",
        "makefile": "#",
        "javascript": "//",
        "typescript": "//",
        "java": "//",
        "c": "//",
        "cpp": "//",
        "cxx": "//",
        "c++": "//",
        "cs": "//",
        "csharp": "//",
        "go": "//",
        "rust": "//",
        "swift": "//",
        "kotlin": "//",
        "scala": "//",
        "php": "//",
        "lua": "--",
        "sql": "--",
        "haskell": "--",
        "elm": "--",
        "html": "<!--",
        "xml": "<!--",
    }

    language_lower = language.lower()
    if language_lower not in comment_styles:
        supported = ", ".join(sorted(comment_styles.keys()))
        msg = (
            f"Language '{language}' is not supported. "
            f"Supported languages: {supported}"
        )
        raise ValueError(msg)

    comment = comment_styles[language_lower]

    # HTML/XML need closing comment markers
    if language_lower in {"html", "xml"}:
        start_template = f"{comment} doccmd-group-delimiter: start-block-{{block_index}} -->"
        end_template = (
            f"{comment} doccmd-group-delimiter: end-block-{{block_index}} -->"
        )
    else:
        start_template = (
            f"{comment} doccmd-group-delimiter: start-block-{{block_index}}"
        )
        end_template = (
            f"{comment} doccmd-group-delimiter: end-block-{{block_index}}"
        )

    return GroupDelimiters(
        start_template=start_template,
        end_template=end_template,
    )


@beartype
def insert_markers(
    *,
    grouped_source: str,
    block_positions: Sequence[BlockPosition],
    delimiters: GroupDelimiters,
) -> str:
    """Insert markers into grouped source to delimit individual blocks.

    Args:
        grouped_source: The combined source from all blocks in the group.
        block_positions: Position information for each block.
        delimiters: The delimiter templates to use.

    Returns:
        The grouped source with markers inserted.
    """
    lines = grouped_source.splitlines(keepends=True)
    result_lines: list[str] = []
    current_line = 0

    for position in block_positions:
        # Add any lines before this block
        while current_line < position.start_line:
            result_lines.append(lines[current_line])
            current_line += 1

        # Add start marker
        start_marker = delimiters.get_start_marker(position.block_index)
        result_lines.append(f"{start_marker}\n")

        # Add block content
        while current_line < position.end_line:
            result_lines.append(lines[current_line])
            current_line += 1

        # Add end marker
        end_marker = delimiters.get_end_marker(position.block_index)
        result_lines.append(f"{end_marker}\n")

    # Add any remaining lines
    while current_line < len(lines):
        result_lines.append(lines[current_line])
        current_line += 1

    return "".join(result_lines)


@beartype
def extract_blocks(
    *,
    marked_source: str,
    delimiters: GroupDelimiters,
) -> list[str]:
    """Extract individual blocks from marked source.

    Args:
        marked_source: The grouped source with delimiter markers.
        delimiters: The delimiter templates used in the source.

    Returns:
        List of individual block contents (without markers).

    Raises:
        ValueError: If markers are malformed or missing.
    """
    lines = marked_source.splitlines(keepends=True)
    blocks: list[str] = []
    current_block_lines: list[str] = []
    inside_block = False
    expected_block_index = 0

    for line_num, line in enumerate(lines, start=1):
        stripped = line.rstrip("\n")

        # Check for start marker
        expected_start = delimiters.get_start_marker(expected_block_index)
        if stripped == expected_start:
            if inside_block:
                msg = (
                    f"Line {line_num}: Found start marker while already "
                    f"inside block {expected_block_index}"
                )
                raise ValueError(msg)
            inside_block = True
            current_block_lines = []
            continue

        # Check for end marker
        expected_end = delimiters.get_end_marker(expected_block_index)
        if stripped == expected_end:
            if not inside_block:
                msg = (
                    f"Line {line_num}: Found end marker without "
                    f"matching start marker for block {expected_block_index}"
                )
                raise ValueError(msg)
            blocks.append("".join(current_block_lines))
            current_block_lines = []
            inside_block = False
            expected_block_index += 1
            continue

        # Regular content line
        if inside_block:
            current_block_lines.append(line)

    if inside_block:
        msg = f"Unclosed block {expected_block_index}: missing end marker"
        raise ValueError(msg)

    return blocks


@beartype
def validate_markers(
    *,
    marked_source: str,
    delimiters: GroupDelimiters,
    expected_block_count: int,
) -> bool:
    """Validate that markers in source are well-formed.

    Args:
        marked_source: The grouped source with delimiter markers.
        delimiters: The delimiter templates used in the source.
        expected_block_count: The number of blocks expected.

    Returns:
        True if markers are valid, False otherwise.
    """
    try:
        blocks = extract_blocks(
            marked_source=marked_source,
            delimiters=delimiters,
        )
        return len(blocks) == expected_block_count
    except ValueError:
        return False
