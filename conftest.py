"""Setup for Sybil."""

import os
import sys
from doctest import ELLIPSIS

import pytest
from beartype import beartype
from sybil import Sybil
from sybil.evaluators.python import PythonEvaluator
from sybil.parsers.rest import (
    ClearNamespaceParser,
    CodeBlockParser,
    DocTestParser,
)
from sybil.sybil import SybilCollection

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


sybil = Sybil(
    parsers=[
        ClearNamespaceParser(),
        DocTestParser(optionflags=ELLIPSIS),
        CodeBlockParser(
            language="shell",
            evaluator=ShellCommandEvaluator(
                args=[
                    sys.executable,
                    "-m",
                    "pre_commit",
                    "run",
                    "--files",
                ],
                tempfile_suffix=".sh",
                pad_file=False,
                write_to_file=False,
            ),
        ),
        CodeBlockParser(
            language="python",
            evaluator=MultiEvaluator(
                evaluators=[
                    PythonEvaluator(),
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
                            "--files",
                        ],
                        env={
                            **os.environ,
                            # These hooks are run separately as they do not
                            # work with file padding.
                            "SKIP": "ruff-format-diff",
                        },
                        tempfile_suffix=".py",
                        pad_file=True,
                        write_to_file=True,
                    ),
                ]
            ),
        ),
    ],
    patterns=["*.rst", "*.py"],
)

sybils = SybilCollection([sybil])
pytest_collect_file = sybils.pytest()
