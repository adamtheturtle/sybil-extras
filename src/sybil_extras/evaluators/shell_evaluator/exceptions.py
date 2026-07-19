"""Exceptions for shell command evaluators."""

from beartype import beartype


@beartype
class InvalidPyconError(ValueError):
    """Raised when pycon content contains lines before the first
    prompt.
    """


@beartype
class PyconOutputMismatchError(ValueError):
    """Raised when a reformatted pycon statement changed its meaning.

    When a command rewrites what a statement does (rather than merely
    reformatting it), the recorded output from the original transcript can
    no longer be safely reattached, so this error is raised instead.
    """
