"""
Lexers for MDX parsing.
"""

import re

from sybil.parsers.abstract.lexers import BlockLexer

DIRECTIVE_IN_JSX_COMMENT_START = (
    r"^(?P<prefix>[ \t]*)\{{/\*\s*(?P<directive>{directive}):?[ \t]*"
    r"(?P<arguments>{arguments})[ \t]*"
    r"(?:$\n|(?=\*/\}}))"
)
DIRECTIVE_IN_JSX_COMMENT_END = r"(?:(?<=\n){prefix})?\*/\}}"


class DirectiveInJSXCommentLexer(BlockLexer):
    """A lexer for faux directives in JSX-style comments.

    Examples:

    .. code-block:: mdx

        {/* directive: argument */}

    Or multi-line:

    .. code-block:: mdx

        {/* directive: argument

            Source here...

        */}

    It extracts the following lexemes:

    - ``directive`` as a :class:`str`.
    - ``arguments`` as a :class:`str`.
    - ``source`` as a :class:`~sybil.Lexeme`.
    """

    def __init__(
        self,
        directive: str,
        arguments: str = ".*?",
        mapping: dict[str, str] | None = None,
    ) -> None:
        """Initialize the lexer.

        Args:
            directive: A regex pattern to match directive names.
            arguments: A regex pattern to match directive arguments.
            mapping: Optional mapping to rename lexemes.
        """
        super().__init__(
            start_pattern=re.compile(
                pattern=DIRECTIVE_IN_JSX_COMMENT_START.format(
                    directive=directive,
                    arguments=arguments,
                ),
                flags=re.MULTILINE,
            ),
            end_pattern_template=DIRECTIVE_IN_JSX_COMMENT_END,
            mapping=mapping,
        )
