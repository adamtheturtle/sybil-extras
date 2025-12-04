"""
A parser that groups all code blocks in an MDX document.
"""

from __future__ import annotations

from beartype import beartype

from sybil_extras.parsers.abstract.group_all import AbstractGroupAllParser


@beartype
class GroupAllParser(AbstractGroupAllParser):
    """
    A parser that groups every code block in a document without markup.
    """
