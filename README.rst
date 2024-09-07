sybil-extras
============

Add ons for `Sybil <http://sybil.readthedocs.io>`_.

Installation
------------

.. code-block:: bash

    pip install sybil-extras

Usage
-----

MultiEvaluator
^^^^^^^^^^^^^^

.. code-block:: python

    """Use MultiEvaluator to run multiple evaluators on the same parser."""

    from sybil import Example, Sybil
    from sybil.parsers.codeblock import CodeBlockParser

    from sybil_extras.evaluators.multi import MultiEvaluator


    def _evaluator_1(example: Example) -> None:
        assert example.given == "1 + 1"
        assert example.expected == "2"


    def _evaluator_2(example: Example) -> None:
        assert example.given == "2 + 2"
        assert example.expected == "4"


    evaluators = [_evaluator_1, _evaluator_2]
    multi_evaluator = MultiEvaluator(evaluators=evaluators)
    parser = CodeBlockParser(language="python", evaluator=multi_evaluator)
    sybil = Sybil(parsers=[parser])

- Add Github RELEASE_PAT
- Create RTD documentation, fix urls.Documentation = "TODO"
- Use meta - this in this project (conftest.py)
- Test with markdown file
- Submit to PyPI
- Use in projects
