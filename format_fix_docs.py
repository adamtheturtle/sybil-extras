"""Script to run ruff format on the given file."""

import shlex
from collections.abc import Iterable, Sequence
from pathlib import Path

import click
from beartype import beartype
from sybil import Sybil
from sybil.parsers.markdown import CodeBlockParser as MarkdownCodeBlockParser
from sybil.parsers.rest import CodeBlockParser as RestCodeBlockParser

from sybil_extras.evaluators.shell_evaluator import ShellCommandEvaluator


@beartype
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


@beartype
@click.command()
@click.option("language", "--language", type=str, required=True)
@click.option("command", "--command", type=str, required=True)
@click.argument(
    "file_paths",
    type=click.Path(exists=True, path_type=Path),
    nargs=-1,
)
def main(language: str, command: str, file_paths: Iterable[Path]) -> None:
    """Run ruff format on the given files."""
    args = shlex.split(s=command)
    for file_path in file_paths:
        _run_args_against_docs(
            args=args,
            file_path=file_path,
            language=language,
        )


if __name__ == "__main__":
    main()
