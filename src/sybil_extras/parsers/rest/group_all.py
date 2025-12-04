"""
A parser that groups all code blocks in a reStructuredText document.
"""

from beartype import beartype

from sybil_extras.parsers.abstract.group_all import AbstractGroupAllParser


@beartype
class GroupAllParser(AbstractGroupAllParser):
    """
    A parser that groups all code blocks in a document without markup.
    """
