"""Tests for the custom directive skip parser for reST."""

from pathlib import Path

from sybil import Sybil

from sybil_extras.parsers.rest.custom_directive_skip import (
    CustomDirectiveSkipParser,
)


def test_skip(tmp_path: Path) -> None:
    """Test that the custom directive skip parser skips the directive."""
    content = """\

    .. code-block:: python

       x = 1

    .. skip: next

    .. code-block:: python

       x = 2

    .. code-block:: python

       x = 3
    """

    test_document = tmp_path / "test.rst"
    test_document.write_text(data=content, encoding="utf-8")

    skip_parser = CustomDirectiveSkipParser(directive="custom-skip")

    sybil = Sybil(parsers=[skip_parser])
    document = sybil.parse(path=test_document)
    examples = list(document)
    breakpoint()
