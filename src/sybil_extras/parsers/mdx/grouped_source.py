"""
A group parser for MDX using the group attribute.
"""

import re
from collections.abc import Iterable

from beartype import beartype
from sybil import Document, Region
from sybil.parsers.markdown.lexers import DirectiveInHTMLCommentLexer
from sybil.typing import Evaluator

from sybil_extras.parsers.abstract.grouped_source import (
    AbstractGroupedSourceParser,
)


@beartype
class GroupedSourceParser(AbstractGroupedSourceParser):
    """A code block group parser for MDX.

    This parser supports two grouping methods:
    1. HTML comment directives (like Markdown): <!-- directive: start/end -->
    2. MDX code block group attribute: ```python group="my-group"

    The comment-based grouping takes precedence for explicit control,
    while the attribute-based grouping provides a more MDX-native approach.
    """

    def __init__(
        self,
        *,
        directive: str,
        evaluator: Evaluator,
        pad_groups: bool,
    ) -> None:
        """
        Args:
            directive: The name of the directive to use for grouping.
                Used for HTML comment style: <!-- directive: start/end -->
            evaluator: The evaluator to use for evaluating the combined region.
            pad_groups: Whether to pad groups with empty lines.
                This is useful for error messages that reference line numbers.
                However, this is detrimental to commands that expect the file
                to not have a bunch of newlines in it, such as formatters.
        """
        # MDX supports HTML comments like Markdown
        lexers = [
            DirectiveInHTMLCommentLexer(
                directive=re.escape(pattern=directive),
            ),
        ]
        super().__init__(
            lexers=lexers,
            evaluator=evaluator,
            directive=directive,
            pad_groups=pad_groups,
        )


@beartype
class GroupAttributeParser:
    """A parser that groups MDX code blocks by their 'group' attribute.

    This parser looks for code blocks with a group="name" attribute and
    combines all blocks with the same group name into a single region.

    Example:
        ```python group="setup"
        x = 1
        ```

        ```python group="setup"
        y = 2
        ```

        Both blocks above will be combined into a single region.
    """

    def __init__(
        self,
        *,
        evaluator: Evaluator,
        pad_groups: bool = True,
        language: str | None = None,
    ) -> None:
        """
        Args:
            evaluator: The evaluator to use for evaluating the combined region.
            pad_groups: Whether to pad groups with empty lines.
            language: If specified, only group blocks of this language.
                If None, groups all code blocks regardless of language.
        """
        self._evaluator = evaluator
        self._pad_groups = pad_groups
        self._language = language

        # Pattern to match MDX code blocks with group attribute
        if language:
            escaped_lang = re.escape(pattern=language)
            self._pattern = re.compile(
                pattern=(
                    rf"^```{escaped_lang}[ \t]+[^\n]*"
                    rf'group="([^"]+)"[^\n]*\n(.*?)^```$'
                ),
                flags=re.MULTILINE | re.DOTALL,
            )
        else:
            self._pattern = re.compile(
                pattern=(
                    r"^```(\w+)[ \t]+[^\n]*"
                    r'group="([^"]+)"[^\n]*\n(.*?)^```$'
                ),
                flags=re.MULTILINE | re.DOTALL,
            )

    def __call__(self, document: Document) -> Iterable[Region]:
        """Parse the document and yield regions for grouped code blocks.

        This parser collects all code blocks with the same group
        attribute and yields a combined region for each group at the
        position of the last block in that group.
        """
        # Collect all blocks by group name
        groups: dict[str, list[tuple[int, int, str, int]]] = {}

        for match in self._pattern.finditer(string=document.text):
            if self._language:
                # Language specified: group(1) is group name, group(2) is code
                group_name = match.group(1)
                code = match.group(2)
            else:
                # No language specified: group(1) is language,
                # group(2) is group name, group(3) is code
                group_name = match.group(2)
                code = match.group(3)

            if group_name not in groups:
                groups[group_name] = []

            # Store tuple: (start_pos, end_pos, code, line_number)
            line_num = document.text[: match.start()].count("\n")
            groups[group_name].append(
                (match.start(), match.end(), code, line_num)
            )

        # Yield combined regions for each group
        for blocks in groups.values():
            # Sort by position to maintain order
            blocks.sort(key=lambda x: x[0])

            # Combine code from all blocks in the group
            combined_code = blocks[0][2]
            first_line = blocks[0][3]

            for _, _, code, line_num in blocks[1:]:
                if self._pad_groups:
                    # Calculate padding to preserve line numbers
                    existing_lines = len(combined_code.splitlines())
                    padding_lines = line_num - first_line - existing_lines
                    padding = "\n" * max(1, padding_lines)
                else:
                    padding = "\n"

                combined_code += padding + code

            # Yield a region at the position of the last block
            last_block = blocks[-1]
            yield Region(
                start=last_block[0],
                end=last_block[1],
                parsed=combined_code,
                evaluator=self._evaluator,
            )
