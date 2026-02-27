"""Exceptions for shell command evaluators."""


class InvalidPyconError(ValueError):
    """Raised when pycon content contains lines before the first
    prompt.
    """
