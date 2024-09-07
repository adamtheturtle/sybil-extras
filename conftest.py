"""Setup for Sybil."""

import os
import sys
from doctest import ELLIPSIS

import pytest
from beartype import beartype
from sybil import Sybil
from sybil.parsers.rest import (
    ClearNamespaceParser,
    CodeBlockParser,
    DocTestParser,
)

from sybil_extras.evaluators.multi import MultiEvaluator
from sybil_extras.evaluators.shell_evaluator import ShellCommandEvaluator


@beartype
def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    """
    Apply the beartype decorator to all collected test functions.
    """
    for item in items:
        if isinstance(item, pytest.Function):
            item.obj = beartype(obj=item.obj)


pytest_collect_file = Sybil(
    parsers=[
        ClearNamespaceParser(),
        DocTestParser(optionflags=ELLIPSIS),
        CodeBlockParser(
            language="python",
            evaluator=MultiEvaluator(
                evaluators=[
                    ShellCommandEvaluator(
                        args=[sys.executable, "-m", "mypy"],
                        pad_file=True,
                        write_to_file=False,
                    ),
                    ShellCommandEvaluator(
                        args=[
                            sys.executable,
                            "-m",
                            "pre_commit",
                            "run",
                            "ruff-format-fix",
                            "--files",
                        ],
                        tempfile_suffix=".py",
                        pad_file=False,
                        write_to_file=True,
                    ),
                    ShellCommandEvaluator(
                        args=[
                            sys.executable,
                            "-m",
                            "pre_commit",
                            "run",
                            "ruff-check-fix",
                            "--files",
                        ],
                        tempfile_suffix=".py",
                        pad_file=False,
                        write_to_file=True,
                    ),
                    ShellCommandEvaluator(
                        args=[
                            sys.executable,
                            "-m",
                            "pre_commit",
                            "run",
                            "--files",
                        ],
                        env={**os.environ, "SKIP": "ruff-format-check"},
                        tempfile_suffix=".py",
                        pad_file=True,
                        write_to_file=False,
                    ),
                ]
            ),
        ),
    ],
    patterns=["*.rst", "*.py"],
).pytest()