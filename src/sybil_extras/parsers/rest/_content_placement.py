"""Structural placement of content within reStructuredText blocks.

reStructuredText directive bodies (such as ``.. code-block::``) are
indented literal blocks: their content is indented relative to the
directive marker and separated from it by a blank line. This module
records that markup-specific placement on each region as lexemes so that
the language-agnostic code block writer can insert content into an
*empty* block without needing to know any reStructuredText formatting.
"""

from beartype import beartype
from sybil import Region

from sybil_extras.evaluators.code_block_writer import (
    CONTENT_INDENT_LEXEME,
    CONTENT_SEPARATOR_LEXEME,
)

_LITERAL_BLOCK_INDENT = "   "
_LITERAL_BLOCK_SEPARATOR = "\n\n"


@beartype
def attach_content_placement(*, region: Region) -> None:
    """Record reStructuredText content placement on ``region``."""
    region.lexemes[CONTENT_INDENT_LEXEME] = _LITERAL_BLOCK_INDENT
    region.lexemes[CONTENT_SEPARATOR_LEXEME] = _LITERAL_BLOCK_SEPARATOR
