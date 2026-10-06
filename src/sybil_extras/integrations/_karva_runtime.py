"""Document lifetime used by generated Karva test modules."""

from collections.abc import Generator, Mapping
from contextlib import contextmanager
from importlib import import_module
from pathlib import Path
from unittest import SkipTest

from beartype import beartype
from karva import skip
from sybil import Document, Example, Sybil
from sybil.sybil import SybilCollection


@beartype
def load_configuration(*, reference: str) -> tuple[Sybil, ...]:
    """Load a module-level Sybil configuration."""
    parts = reference.split(sep=":", maxsplit=1)
    if len(parts) != len(("module", "attribute")) or not all(parts):
        message = "Configuration must be a module:attribute reference"
        raise ValueError(message)
    module, attribute = parts
    if not attribute.isidentifier():
        message = "Configuration attribute must be a Python identifier"
        raise ValueError(message)
    configuration: object = vars(import_module(name=module))[attribute]
    if isinstance(configuration, Sybil):
        return (configuration,)
    if isinstance(configuration, SybilCollection):
        return tuple(configuration)
    message = f"{reference} must refer to a Sybil or SybilCollection"
    raise TypeError(message)


@beartype
class DocumentTests:
    """Retain a document's namespace and example sequence in one
    worker.
    """

    def __init__(self, *, sybil: Sybil, path: Path) -> None:
        """Parse one document without evaluating or setting it up."""
        self.sybil = sybil
        self.document: Document = sybil.parse(path=path)
        self.examples = tuple(self.document.examples())

    @contextmanager
    # Python 3.11 needs all three generator type arguments.
    def lifecycle(self) -> Generator["DocumentTests", None, None]:  # pylint: disable=unnecessary-default-type-args
        """Set up once and tear down even if an example fails."""
        if self.sybil.setup is not None:
            self.sybil.setup(self.document.namespace)
        try:
            yield self
        finally:
            if self.sybil.teardown is not None:
                self.sybil.teardown(self.document.namespace)

    def evaluate(
        self, *, example: Example, fixtures: Mapping[str, object]
    ) -> None:
        """Inject this example's fixture values and evaluate it."""
        self.document.namespace.update(fixtures)
        try:
            example.evaluate()
        except SkipTest as error:
            skip(reason=str(object=error))


@beartype
def load_document(
    *, reference: str, configuration_index: int, path: Path
) -> DocumentTests:
    """Recreate a generated module's document in the executing worker."""
    return DocumentTests(
        sybil=load_configuration(reference=reference)[configuration_index],
        path=path,
    )
