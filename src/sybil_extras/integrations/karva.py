"""Generate native Karva tests for Sybil documentation examples."""

import keyword
from collections.abc import Sequence
from pathlib import Path

from beartype import beartype

from sybil_extras.integrations._karva_runtime import (
    DocumentTests,
    load_configuration,
)

_RESERVED_FIXTURES = frozenset({"_sybil_example", "_sybil_document"})


@beartype
def _module_source(
    *, reference: str, configuration_index: int, suite: DocumentTests
) -> str:
    """Render source that Karva can collect without importing Python."""
    fixtures = suite.sybil.fixtures
    for name in fixtures:
        if (
            not name.isidentifier()
            or keyword.iskeyword(name)
            or name in _RESERVED_FIXTURES
        ):
            message = f"Unsupported Sybil fixture name: {name!r}"
            raise ValueError(message)
    arguments = ", ".join(
        ("_sybil_example", "_sybil_document", *dict.fromkeys(fixtures))
    )
    values = ", ".join(f"{name!r}: {name}" for name in dict.fromkeys(fixtures))
    return f'''"""Generated Sybil examples. Regenerate instead of editing."""
from pathlib import Path
import karva
from sybil_extras.integrations._karva_runtime import load_document

_suite = load_document(
    reference={reference!r},
    configuration_index={configuration_index},
    path=Path({suite.document.path!r}),
)

@karva.fixture(scope="module")
def _sybil_document():
    with _suite.lifecycle() as document:
        yield document

@karva.tags.parametrize(
    "_sybil_example",
    tuple(
        karva.param(
            example,
            id=f"{{example.path}}:{{_suite.sybil.identify(example)}}",
        )
        for example in _suite.examples
    ),
)
def test_examples({arguments}):
    _sybil_document.evaluate(example=_sybil_example, fixtures={{{values}}})
'''


@beartype
def generate_karva_tests(
    *, reference: str, paths: Sequence[Path], destination: Path
) -> tuple[Path, ...]:
    """Write one native test module per matching document and
    configuration.

    ``reference`` names an importable module-level ``Sybil`` or
    ``SybilCollection`` as ``module:attribute``. ``paths`` explicitly selects
    documentation files or directories. ``destination`` must be empty and
    should be inside the project so ancestor ``conftest.py`` fixtures apply.
    """
    if destination.exists() and any(destination.iterdir()):
        message = f"Generated test directory must be empty: {destination}"
        raise ValueError(message)
    documents = sorted(
        {
            file.absolute()
            for path in paths
            for file in (path.rglob(pattern="*") if path.is_dir() else (path,))
            if file.is_file()
            and destination.resolve() not in file.resolve().parents
        }
    )
    modules: list[str] = []
    matched: set[Path] = set()
    for index, sybil in enumerate(
        iterable=load_configuration(reference=reference)
    ):
        for path in documents:
            if sybil.should_parse(path=path):
                if path in matched:
                    message = f"Overlapping Sybil configurations: {path}"
                    raise ValueError(message)
                matched.add(path)
                suite = DocumentTests(sybil=sybil, path=path)
                if len(suite.examples) > 0:
                    modules.append(
                        _module_source(
                            reference=reference,
                            configuration_index=index,
                            suite=suite,
                        )
                    )
    destination.mkdir(parents=True, exist_ok=True)
    generated: list[Path] = []
    for index, source in enumerate(iterable=modules):
        target = destination / f"test_sybil_{index:04d}.py"
        _ = target.write_text(data=source, encoding="utf-8")
        generated.append(target)
    return tuple(generated)
