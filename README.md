[![Build
Status](https://github.com/adamtheturtle/sybil-extras/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/adamtheturtle/sybil-extras/actions)
[![codecov](https://codecov.io/gh/adamtheturtle/sybil-extras/branch/main/graph/badge.svg)](https://codecov.io/gh/adamtheturtle/sybil-extras)
[![PyPI](https://badge.fury.io/py/sybil-extras.svg)](https://badge.fury.io/py/sybil-extras)

# sybil-extras

Add ons for [Sybil](http://sybil.readthedocs.io).

## Installation

``` shell
$ pip install sybil-extras
```

## Usage

### MultiEvaluator

``` python
"""Use MultiEvaluator to run multiple evaluators on the same parser."""

from sybil import Example, Sybil
from sybil.evaluators.python import PythonEvaluator
from sybil.parsers.codeblock import CodeBlockParser
from sybil.typing import Evaluator

from sybil_extras.evaluators.multi import MultiEvaluator


def _evaluator_1(example: Example) -> None:
    """Check that the example is long enough."""
    minimum_length = 50
    assert len(example.parsed) >= minimum_length


evaluators = [_evaluator_1, PythonEvaluator()]
multi_evaluator = MultiEvaluator(evaluators=evaluators)
parser = CodeBlockParser(language="python", evaluator=multi_evaluator)
sybil = Sybil(parsers=[parser])
```

### ShellCommandEvaluator

``` python
"""Use ShellCommandEvaluator to run shell commands against the code block."""

import sys

from sybil import Sybil
from sybil.parsers.codeblock import CodeBlockParser

from sybil_extras.evaluators.shell_evaluator import ShellCommandEvaluator

evaluator = ShellCommandEvaluator(
    args=[sys.executable, "-m", "mypy"],
    # The code block is written to a temporary file
    # with this suffix.
    tempfile_suffix=".py",
    # Pad the temporary file with newlines so that the
    # line numbers in the error messages match the
    # line numbers in the source document.
    pad_file=True,
    # Don't write any changes back to the source document.
    # This option is useful when running a linter or formatter
    # which modifies the code.
    write_to_file=False,
)
parser = CodeBlockParser(language="python", evaluator=evaluator)
sybil = Sybil(parsers=[parser])
```
