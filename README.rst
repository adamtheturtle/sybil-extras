|Build Status| |codecov| |PyPI|

sybil-extras
============

Add ons for `Sybil <http://sybil.readthedocs.io>`_.

Installation
------------

.. code-block:: shell

    $ pip install sybil-extras

Usage
-----

MultiEvaluator
^^^^^^^^^^^^^^

.. code-block:: python

    """Use MultiEvaluator to run multiple evaluators on the same parser."""

    from sybil import Example, Sybil
    from sybil.evaluators.python import PythonEvaluator
    from sybil.parsers.rest.codeblock import CodeBlockParser
    from sybil.typing import Evaluator

    from sybil_extras.evaluators.multi import MultiEvaluator


    def _evaluator_1(example: Example) -> None:
        """Check that the example is long enough."""
        minimum_length = 50
        assert len(example.parsed) >= minimum_length


    evaluators: list[Evaluator] = [_evaluator_1, PythonEvaluator()]
    multi_evaluator = MultiEvaluator(evaluators=evaluators)
    parser = CodeBlockParser(language="python", evaluator=multi_evaluator)
    sybil = Sybil(parsers=[parser])

    pytest_collect_file = sybil.pytest()

ShellCommandEvaluator
^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

    """Use ShellCommandEvaluator to run shell commands against the code block."""

    import sys

    from sybil import Sybil
    from sybil.parsers.rest.codeblock import CodeBlockParser

    from sybil_extras.evaluators.shell_evaluator import ShellCommandEvaluator

    evaluator = ShellCommandEvaluator(
        args=[sys.executable, "-m", "mypy"],
        # The code block is written to a temporary file
        # with these suffixes.
        tempfile_suffixes=[".example", ".py"],
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

    pytest_collect_file = sybil.pytest()

CustomDirectiveSkipParser
^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

    """Use CustomDirectiveSkipParser to skip code blocks with a custom marker."""

    from sybil import Sybil
    from sybil.parsers.rest.codeblock import PythonCodeBlockParser

    # Similar parsers are available at
    # sybil_extras.parsers.markdown.custom_directive_skip and
    # sybil_extras.parsers.myst.custom_directive_skip.
    from sybil_extras.parsers.rest.custom_directive_skip import (
        CustomDirectiveSkipParser,
    )

    skip_parser = CustomDirectiveSkipParser(directive="custom-marker-skip")
    code_block_parser = PythonCodeBlockParser()

    sybil = Sybil(parsers=[skip_parser, code_block_parser])

    pytest_collect_file = sybil.pytest()

This allows you to skip code blocks in the same way as described in
the Sybil documentation for skipping examples in
`reStructuredText <https://sybil.readthedocs.io/en/latest/rest.html#skipping-examples>`_,
`Markdown <https://sybil.readthedocs.io/en/latest/rest.html#skipping-examples>`_ ,
and `MyST <https://sybil.readthedocs.io/en/latest/myst.html#skipping-examples>`_ files,
but with custom text, e.g. ``custom-marker-skip`` replacing the word ``skip``.

.. |Build Status| image:: https://github.com/adamtheturtle/sybil-extras/actions/workflows/ci.yml/badge.svg?branch=main
   :target: https://github.com/adamtheturtle/sybil-extras/actions
.. |codecov| image:: https://codecov.io/gh/adamtheturtle/sybil-extras/branch/main/graph/badge.svg
   :target: https://codecov.io/gh/adamtheturtle/sybil-extras
.. |PyPI| image:: https://badge.fury.io/py/sybil-extras.svg
   :target: https://badge.fury.io/py/sybil-extras
