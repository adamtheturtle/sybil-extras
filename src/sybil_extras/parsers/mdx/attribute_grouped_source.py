"""An attribute-based group parser for MDX.

This parser groups code blocks based on the 'group' attribute in MDX
fenced code blocks, following Docusaurus conventions.
"""

from beartype import beartype

from sybil_extras.parsers.abstract.attribute_grouped_source import (
    AbstractAttributeGroupedSourceParser,
)


@beartype
class AttributeGroupedSourceParser(AbstractAttributeGroupedSourceParser):
    """A parser for grouping MDX code blocks by attribute values.

    This parser groups code blocks that have the same value for a
    specified attribute (default: 'group').
    """
