"""Run generated documentation tests with the real Karva executable."""

import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

import pytest

from sybil_extras.integrations.karva import generate_karva_tests


@pytest.mark.parametrize(
    argnames="arguments",
    argvalues=(
        [],
        ["--num-workers=2"],
        ["--num-workers=2", "--random-seed=23"],
    ),
)
def test_document_lifecycle(
    *,
    tmp_path: Path,
    run_karva: Callable[[Path, list[str]], subprocess.CompletedProcess[str]],
    arguments: list[str],
) -> None:
    """Keep each document namespace ordered and inject fresh fixtures per
    example.
    """
    project = tmp_path / "project"
    project.mkdir()
    config = project / "sybil_config.py"
    _ = config.write_text(
        data="""from pathlib import Path
from sybil import Sybil
from sybil.parsers.rest import DocTestParser

def setup(namespace):
    namespace["counter"] = 0
    with open("events.txt", "a") as events:
        events.write("setup\\n")

def teardown(namespace):
    assert namespace["counter"] == 3
    with open("events.txt", "a") as events:
        events.write("teardown\\n")

sybil = Sybil(parsers=[DocTestParser()], path=str(Path(__file__).parent),
              patterns=["*.rst"], fixtures=["fresh", "shared"],
              setup=setup, teardown=teardown)
""",
        encoding="utf-8",
    )
    _ = (project / "conftest.py").write_text(
        data="""import karva

@karva.fixture(scope="module")
def shared():
    return []

@karva.fixture
def fresh():
    with open("events.txt", "a") as events:
        events.write("fixture setup\\n")
    yield []
    with open("events.txt", "a") as events:
        events.write("fixture teardown\\n")
""",
        encoding="utf-8",
    )
    source = """>>> assert fresh == []
>>> fresh.append("value"); shared.append("value"); counter += 1
>>> assert shared == ["value"]; assert counter == 1; counter += 2
"""
    for name in ("one.rst", "two.rst"):
        _ = (project / name).write_text(data=source, encoding="utf-8")
    # Import the real configuration before generating tests, then remove only
    # this test's import-path entry and module to keep projects independent.
    _ = _generate(project=project)
    result = run_karva(project, arguments)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "6 tests run: 6 passed, 0 skipped" in result.stdout
    events = (project / "events.txt").read_text(encoding="utf-8").splitlines()
    assert sorted(events) == sorted(
        ["setup", "teardown"] * len(("one.rst", "two.rst"))
        + ["fixture setup", "fixture teardown"] * len((1, 2, 3, 4, 5, 6))
    )


def _generate(*, project: Path) -> tuple[Path, ...]:
    """Load this temporary project's genuine module-level
    configuration.
    """
    sys.path.insert(0, str(object=project))
    try:
        return generate_karva_tests(
            reference="sybil_config:sybil",
            paths=[project],
            destination=project / "generated",
        )
    finally:
        sys.path.remove(str(object=project))
        _ = sys.modules.pop("sybil_config", None)


def test_failure_and_skip(
    *,
    tmp_path: Path,
    run_karva: Callable[[Path, list[str]], subprocess.CompletedProcess[str]],
) -> None:
    """Report failures and skips separately and continue before
    cleanup.
    """
    _ = (tmp_path / "sybil_config.py").write_text(
        data="""from pathlib import Path
from sybil import Sybil
from sybil.parsers.rest import DocTestParser, SkipParser

def teardown(namespace):
    assert namespace["after_failure"] == 42
    Path("cleanup.txt").write_text("complete")

sybil = Sybil(parsers=[DocTestParser(), SkipParser()],
              path=str(Path(__file__).parent),
              patterns=["*.rst"], teardown=teardown)
""",
        encoding="utf-8",
    )
    _ = (tmp_path / "example.rst").write_text(
        data=""">>> 1 + 1
3
>>> after_failure = 42

.. skip: next "reason"

>>> raise RuntimeError("must be skipped")
""",
        encoding="utf-8",
    )
    _ = _generate(project=tmp_path)
    result = run_karva(tmp_path, ["--num-workers=2", "--status-level=all"])
    assert result.returncode == 1, result.stdout + result.stderr
    assert "line:1,column:1" in result.stdout
    assert "Example at" in result.stdout
    assert "example.rst, line 1, column 1" in result.stdout
    assert "Expected:" in result.stdout
    assert "Got:" in result.stdout
    assert "4 tests run: 2 passed, 1 failed, 1 skipped" in result.stdout
    assert (tmp_path / "cleanup.txt").read_text(encoding="utf-8") == "complete"


@pytest.mark.parametrize(
    argnames=("filename", "parser_import", "source"),
    argvalues=(
        (
            "example.py",
            "from sybil.parsers.rest import DocTestParser",
            '"""\n>>> value = 42\n>>> value\n42\n"""\n',
        ),
        (
            "example.md",
            "from sybil.parsers.markdown import PythonCodeBlockParser",
            (
                "```python\nvalue = 42\n```\n\n"
                "```python\nassert value == 42\n```\n"
            ),
        ),
    ),
)
def test_document_formats(
    *,
    tmp_path: Path,
    run_karva: Callable[[Path, list[str]], subprocess.CompletedProcess[str]],
    filename: str,
    parser_import: str,
    source: str,
) -> None:
    """Use Sybil's Python and Markdown document parsers unchanged."""
    parser = (
        "DocTestParser()"
        if filename.endswith(".py")
        else "PythonCodeBlockParser()"
    )
    configuration = (
        "from pathlib import Path\nfrom sybil import Sybil\n"
        + parser_import
        + f"\nsybil = Sybil(parsers=[{parser}], "
        + "path=str(Path(__file__).parent), "
        + f"filenames=[{filename!r}])\n"
    )
    _ = (tmp_path / "sybil_config.py").write_text(
        data=configuration, encoding="utf-8"
    )
    _ = (tmp_path / filename).write_text(data=source, encoding="utf-8")
    _ = _generate(project=tmp_path)
    result = run_karva(tmp_path, ["--num-workers=2"])
    assert result.returncode == 0, result.stdout + result.stderr
    assert "2 tests run: 2 passed, 0 skipped" in result.stdout
