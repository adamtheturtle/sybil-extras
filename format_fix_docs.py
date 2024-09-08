"""Script to run ruff format on the given file."""

import sys
from collections.abc import Iterable
from pathlib import Path

from sybil import Sybil
from sybil.parsers.markdown import CodeBlockParser as MarkdownCodeBlockParser
from sybil.parsers.rest import CodeBlockParser as RestCodeBlockParser

from sybil_extras.evaluators.shell_evaluator import ShellCommandEvaluator


def _run_ruff_format(file_path: Path) -> None:
    """Run ruff format on the given file."""
    evaluator = ShellCommandEvaluator(
        args=[
            sys.executable,
            "-m",
            "ruff",
            "format",
        ],
        tempfile_suffix=".py",
        pad_file=True,
        write_to_file=True,
    )

    rest_parser = RestCodeBlockParser(language="python", evaluator=evaluator)
    markdown_parser = MarkdownCodeBlockParser(
        language="python",
        evaluator=evaluator,
    )
    sybil = Sybil(parsers=[rest_parser, markdown_parser])
    document = sybil.parse(path=file_path)
    for example in document:
        example.evaluate()


def main(file_paths: Iterable[Path]) -> None:
    """Run ruff format on the given files."""
    for file_path in file_paths:
        _run_ruff_format(file_path=file_path)


if __name__ == "__main__":
    FILE_PATHS = [Path(item) for item in sys.argv[1:]]
    main(file_paths=FILE_PATHS)
