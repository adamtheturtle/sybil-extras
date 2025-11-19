"""
A parser that groups all code blocks in a reStructuredText document.
"""

from sybil_extras.parsers.abstract.group_all import AbstractGroupAllParser


class GroupAllParser(AbstractGroupAllParser):
    """
    A parser that groups all code blocks in a document without markup.
    """
