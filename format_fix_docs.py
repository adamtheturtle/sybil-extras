"""Script to run ruff format on the given file."""

import sys
from pathlib import Path

from sybil import Sybil
from sybil.parsers.codeblock import CodeBlockParser

from sybil_extras.evaluators.shell_evaluator import ShellCommandEvaluator


def main(file_path: Path) -> None:
    """Run ruff format on the given file."""
    evaluator = ShellCommandEvaluator(
        args=[
            sys.executable,
            "-m",
            "ruff",
            "format",
        ],
        tempfile_suffix=".py",
        pad_file=False,
        write_to_file=True,
    )

    parser = CodeBlockParser(language="python", evaluator=evaluator)
    sybil = Sybil(parsers=[parser])
    document = sybil.parse(path=file_path)
    for example in document:
        example.evaluate()


if __name__ == "__main__":
    FILE_PATH = Path(sys.argv[1])
    main(file_path=FILE_PATH)
