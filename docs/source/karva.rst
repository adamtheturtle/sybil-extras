Karva
=====

Install the optional integration with ``pip install sybil-extras[karva]``.
The ``generate_karva_tests`` function converts a module-level Sybil configuration into Python modules that Karva can collect.
Run generation from your project root and place the generated directory inside that project so its ``conftest.py`` fixtures apply.

Export your existing Sybil instance as ``sybil`` from an importable module, such as ``conftest.py``.
Keep ``pytest_collect_file = sybil.pytest()`` while validating the migration.
Use explicit source paths to avoid including virtual environments or generated files in documentation discovery.

.. code-block:: python

    """Generate native Karva modules for the README examples."""

    from pathlib import Path
    from tempfile import TemporaryDirectory

    from sybil_extras.integrations.karva import generate_karva_tests

    with TemporaryDirectory(dir=".", prefix="karva_sybil_") as directory:
        _ = generate_karva_tests(
            reference="conftest:sybil",
            paths=[Path("README.rst")],
            destination=Path(directory),
        )

While that directory exists, run ``karva test <directory>`` from the project root.
A script can invoke Karva as a subprocess before leaving the context manager.
Install Karva in the environment used by that script.

Each matching document becomes one native test module with dynamically parametrized examples.
Karva runs those examples in source order in one worker, with a shared document namespace and one setup and teardown per document.
Function fixtures are injected anew for each example, and module fixtures are scoped to the document.
Sybil skip exceptions become native Karva skips.
Failures are reported individually, subsequent examples continue, and document teardown runs after failures.

``reference`` accepts a ``Sybil`` or a ``SybilCollection``.
Collection members must select disjoint files.
Overlapping configurations are rejected because separate generated modules would change the lifetime of module fixtures for the same source file.
Fixture names must be Python identifiers and must not be ``_sybil_example`` or ``_sybil_document``.
The output directory must be empty, and generation never overwrites its files.

The example identifier includes its original path, line, and column.
Karva's primary diagnostic still points to the generated test function.
Native source locations are tracked in `Karva issue 1513 <https://github.com/MatthewMckee4/karva/issues/1513>`_.
Temporary module paths also prevent useful reuse of Karva's test history across runs.
Selecting only a later example does not recreate the namespace established by earlier examples, and retries can repeat namespace mutations.
Use full document runs without retries during this pilot.
A native ``Sybil.karva()`` integration is tracked in `Sybil issue 173 <https://github.com/simplistix/sybil/issues/173>`_.
