"""Script to run ruff format on the given file."""

import shlex
from collections.abc import Iterable, Sequence
from pathlib import Path

import click
from beartype import beartype
from pygments.lexers import get_all_lexers
from sybil import Sybil
from sybil.parsers.markdown import CodeBlockParser as MarkdownCodeBlockParser
from sybil.parsers.rest import CodeBlockParser as RestCodeBlockParser

from sybil_extras.evaluators.shell_evaluator import ShellCommandEvaluator


def _map_languages_to_suffix() -> dict[str, str]:
    """
    Map programming languages to their corresponding file extension.
    """
    language_extension_map: dict[str, str] = {}

    for lexer in get_all_lexers():
        language_name = lexer[0]
        file_extensions = lexer[2]
        if file_extensions:
            canonical_file_extension = file_extensions[0]
            if canonical_file_extension.startswith("*."):
                canonical_file_suffix = canonical_file_extension[1:]
                language_extension_map[language_name.lower()] = (
                    canonical_file_suffix
                )

    return language_extension_map


@beartype
def _run_args_against_docs(
    file_path: Path,
    args: Sequence[str | Path],
    language: str,
) -> None:
    """Run commands on the given file."""
    language_to_suffix = _map_languages_to_suffix()
    suffix = language_to_suffix.get(language.lower(), ".txt")
    evaluator = ShellCommandEvaluator(
        args=args,
        tempfile_suffix=suffix,
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
