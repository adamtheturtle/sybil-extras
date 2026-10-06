"""Real Karva processes for integration tests."""

import os
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

import pytest


@pytest.fixture(name="run_karva")
def fixture_run_karva() -> Callable[
    [Path, list[str]], subprocess.CompletedProcess[str]
]:
    """Run Karva in the example project, using this Python environment."""

    def run(
        project: Path, arguments: list[str]
    ) -> subprocess.CompletedProcess[str]:
        """Run a generated project's tests and capture its report."""
        return subprocess.run(  # noqa: S603
            args=[
                sys.executable,
                "-m",
                "karva",
                "test",
                "generated",
                *arguments,
            ],
            cwd=project,
            env={**os.environ, "VIRTUAL_ENV": sys.prefix},
            text=True,
            capture_output=True,
            check=False,
        )

    return run
