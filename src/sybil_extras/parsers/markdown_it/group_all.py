"""A parser that groups all code blocks in a Markdown document.

This parser uses the MarkdownIt library.
"""

from beartype import beartype

from sybil_extras.parsers.abstract.group_all import AbstractGroupAllParser


@beartype
class GroupAllParser(AbstractGroupAllParser):
    """
    A parser that groups all code blocks in a document without markup.
    """
