"""Exceptions for shell command evaluators."""

from beartype import beartype


@beartype
class InvalidPyconError(ValueError):
    """Raised when pycon content contains lines before the first
    prompt.
    """
