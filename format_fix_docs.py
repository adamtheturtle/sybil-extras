"""Script to run ruff format on the given file."""

import sys
from collections.abc import Iterable, Sequence
from pathlib import Path

import click
from sybil import Sybil
from sybil.parsers.markdown import CodeBlockParser as MarkdownCodeBlockParser
from sybil.parsers.rest import CodeBlockParser as RestCodeBlockParser

from sybil_extras.evaluators.shell_evaluator import ShellCommandEvaluator


def _run_args_against_docs(
    file_path: Path,
    args: Sequence[str | Path],
    language: str,
) -> None:
    """Run ruff format on the given file."""
    evaluator = ShellCommandEvaluator(
        args=args,
        tempfile_suffix=".py",
        pad_file=True,
        write_to_file=True,
    )

    rest_parser = RestCodeBlockParser(language=language, evaluator=evaluator)
    markdown_parser = MarkdownCodeBlockParser(
        language=language,
        evaluator=evaluator,
    )
    sybil = Sybil(parsers=[rest_parser, markdown_parser])
    document = sybil.parse(path=file_path)
    for example in document:
        example.evaluate()


@click.command()
@click.argument("file_paths", type=click.Path(exists=True), nargs=-1)
def main(file_paths: Iterable[Path]) -> None:
    """Run ruff format on the given files."""
    args = [
        sys.executable,
        "-m",
        "ruff",
        "format",
    ]
    language = "python"
    for file_path in file_paths:
        _run_args_against_docs(
            args=args,
            file_path=file_path,
            language=language,
        )


if __name__ == "__main__":
    main()
