"""Selection and configuration validation for generated tests."""

import sys
from collections.abc import Generator
from pathlib import Path

import pytest

from sybil_extras.integrations._karva_runtime import (
    load_configuration,
    load_document,
)
from sybil_extras.integrations.karva import generate_karva_tests


@pytest.fixture(name="reference")
def fixture_reference(*, tmp_path: Path) -> Generator[str, None, None]:  # pylint: disable=unnecessary-default-type-args
    """Provide an importable configuration with disjoint Sybil
    instances.
    """
    _ = (tmp_path / "generation_config.py").write_text(
        data="""from pathlib import Path
from sybil import Sybil
from sybil.parsers.rest import DocTestParser
root = str(Path(__file__).parent)
rst = Sybil(parsers=[DocTestParser()], path=root, patterns=["*.rst"],
            excludes=["excluded.rst"])
python = Sybil(parsers=[DocTestParser()], path=root, patterns=["*.py"])
combined = rst + python
overlapping = rst + rst
invalid = 42
""",
        encoding="utf-8",
    )
    sys.path.insert(0, str(object=tmp_path))
    try:
        yield "generation_config:combined"
    finally:
        sys.path.remove(str(object=tmp_path))
        _ = sys.modules.pop("generation_config", None)


def test_selection(*, tmp_path: Path, reference: str) -> None:
    """Select documents once, honor excludes, and ignore empty
    documents.
    """
    for name in ("selected.rst", "excluded.rst"):
        _ = (tmp_path / name).write_text(
            data=">>> 1 + 1\n2\n", encoding="utf-8"
        )
    _ = (tmp_path / "empty.rst").write_text(
        data="Just prose\n", encoding="utf-8"
    )
    _ = (tmp_path / "ignored.txt").write_text(
        data=">>> 1 + 1\n3\n", encoding="utf-8"
    )
    generated = generate_karva_tests(
        reference=reference,
        paths=[tmp_path, tmp_path / "selected.rst", tmp_path / "missing"],
        destination=tmp_path / "generated",
    )
    assert generated == (tmp_path / "generated" / "test_sybil_0000.py",)
    suite = load_document(
        reference=reference,
        configuration_index=0,
        path=tmp_path / "selected.rst",
    )
    (example,) = suite.examples
    with suite.lifecycle():
        suite.evaluate(example=example, fixtures={})


def test_destination(*, tmp_path: Path, reference: str) -> None:
    """Keep existing files intact and accept an existing empty
    directory.
    """
    destination = tmp_path / "generated"
    destination.mkdir()
    expected: tuple[Path, ...] = ()
    assert (
        generate_karva_tests(
            reference=reference, paths=[tmp_path], destination=destination
        )
        == expected
    )
    original = destination / "existing.py"
    _ = original.write_text(data="original", encoding="utf-8")
    with pytest.raises(expected_exception=ValueError, match="must be empty"):
        _ = generate_karva_tests(
            reference=reference, paths=[tmp_path], destination=destination
        )
    assert original.read_text(encoding="utf-8") == "original"


@pytest.mark.parametrize(
    argnames="reference",
    argvalues=("", "module", ":attribute", "module:", "module:bad-name"),
)
def test_invalid_reference(reference: str) -> None:
    """Reject invalid references before importing a module."""
    with pytest.raises(expected_exception=ValueError, match="Configuration"):
        _ = load_configuration(reference=reference)


def test_wrong_configuration(*, reference: str) -> None:
    """Reject exported values that are not Sybil configurations."""
    del reference
    with pytest.raises(
        expected_exception=TypeError, match="must refer to a Sybil"
    ):
        _ = load_configuration(reference="generation_config:invalid")


@pytest.mark.parametrize(
    argnames="fixture_name",
    argvalues=("bad-name", "class", "_sybil_example", "_sybil_document"),
)
def test_invalid_fixture(
    *, tmp_path: Path, reference: str, fixture_name: str
) -> None:
    """Reject names that cannot be represented as native fixture arguments."""
    (sybil,) = load_configuration(reference="generation_config:rst")
    sybil.fixtures = (fixture_name,)
    _ = (tmp_path / "example.rst").write_text(
        data=">>> 1 + 1\n2\n", encoding="utf-8"
    )
    with pytest.raises(
        expected_exception=ValueError, match="Unsupported Sybil fixture"
    ):
        _ = generate_karva_tests(
            reference=reference,
            paths=[tmp_path],
            destination=tmp_path / "generated",
        )


def test_overlapping_configurations(*, tmp_path: Path, reference: str) -> None:
    """Reject splitting a file's module fixture across configurations."""
    del reference
    _ = (tmp_path / "example.rst").write_text(
        data=">>> 1 + 1\n2\n", encoding="utf-8"
    )
    with pytest.raises(
        expected_exception=ValueError, match="Overlapping Sybil configurations"
    ):
        _ = generate_karva_tests(
            reference="generation_config:overlapping",
            paths=[tmp_path],
            destination=tmp_path / "generated",
        )
