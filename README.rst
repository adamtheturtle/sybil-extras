|Build Status| |PyPI|

sybil-extras
============

.. contents::
   :local:

Add ons for `Sybil <http://sybil.readthedocs.io>`_.

Installation
------------

.. code-block:: shell

    $ pip install sybil-extras

Evaluators
----------

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
        # Use a pseudo-terminal for running commands.
        # This can be useful e.g. to get color output, but can also break
        # in some environments.
        use_pty=True,
    )
    parser = CodeBlockParser(language="python", evaluator=evaluator)
    sybil = Sybil(parsers=[parser])

    pytest_collect_file = sybil.pytest()

BlockAccumulatorEvaluator
^^^^^^^^^^^^^^^^^^^^^^^^^

The ``BlockAccumulatorEvaluator`` accumulates parsed code block content in a list within the document's namespace.
This is useful for testing parsers that group multiple code blocks together.

.. code-block:: python

    """Use BlockAccumulatorEvaluator to accumulate code blocks."""

    from pathlib import Path

    from sybil import Sybil
    from sybil.parsers.rest.codeblock import CodeBlockParser

    from sybil_extras.evaluators.block_accumulator import BlockAccumulatorEvaluator

    namespace_key = "blocks"
    evaluator = BlockAccumulatorEvaluator(namespace_key=namespace_key)
    parser = CodeBlockParser(language="python", evaluator=evaluator)
    sybil = Sybil(parsers=[parser])
    document = sybil.parse(path=Path("README.rst"))

    for example in document.examples():
        example.evaluate()

    blocks = document.namespace[namespace_key]
    assert len(blocks)

NoOpEvaluator
^^^^^^^^^^^^^

The ``NoOpEvaluator`` is an evaluator which does nothing.
It is useful for testing and debugging parsers.

.. code-block:: python

    """Use NoOpEvaluator to do nothing."""

    from sybil import Sybil
    from sybil.parsers.rest.codeblock import CodeBlockParser

    from sybil_extras.evaluators.no_op import NoOpEvaluator

    parser = CodeBlockParser(language="python", evaluator=NoOpEvaluator())
    sybil = Sybil(parsers=[parser])

    pytest_collect_file = sybil.pytest()

CodeBlockWriterEvaluator
^^^^^^^^^^^^^^^^^^^^^^^^

The ``CodeBlockWriterEvaluator`` wraps another evaluator and writes any modifications back to the source document.
This is useful for building evaluators that transform code blocks, such as formatters or auto-fixers.

The wrapped evaluator should store the modified content in ``example.document.namespace[namespace_key]`` for it to be written back.

.. code-block:: python

    """Use CodeBlockWriterEvaluator to write modifications back to code blocks."""

    from sybil import Example, Sybil
    from sybil.parsers.rest.codeblock import CodeBlockParser

    from sybil_extras.evaluators.code_block_writer import CodeBlockWriterEvaluator


    def formatting_evaluator(example: Example) -> None:
        """Format the code and store the result for writing back."""
        formatted_code = example.parsed.upper()
        example.document.namespace["modified_content"] = formatted_code


    writer_evaluator = CodeBlockWriterEvaluator(
        evaluator=formatting_evaluator,
        # The key in example.document.namespace where modified content is stored.
        # Defaults to "modified_content".
        namespace_key="modified_content",
        # Optional encoding for writing files.
        encoding=None,
    )
    parser = CodeBlockParser(language="python", evaluator=writer_evaluator)
    sybil = Sybil(parsers=[parser])

    pytest_collect_file = sybil.pytest()

Parsers
-------

CustomDirectiveSkipParser
^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

    """Use CustomDirectiveSkipParser to skip code blocks with a custom marker."""

    from sybil import Sybil
    from sybil.parsers.rest.codeblock import PythonCodeBlockParser

    # Similar parsers are available at
    # sybil_extras.parsers.markdown.custom_directive_skip,
    # sybil_extras.parsers.mdx.custom_directive_skip and
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
MDX, and `MyST <https://sybil.readthedocs.io/en/latest/myst.html#skipping-examples>`_ files,
but with custom text, e.g. ``custom-marker-skip`` replacing the word ``skip``.

GroupedSourceParser
^^^^^^^^^^^^^^^^^^^

.. code-block:: python

    """Use GroupedSourceParser to group code blocks by a custom directive."""

    import sys
    from pathlib import Path

    from sybil import Sybil
    from sybil.example import Example
    from sybil.parsers.rest.codeblock import PythonCodeBlockParser

    # Similar parsers are available at
    # sybil_extras.parsers.markdown.grouped_source,
    # sybil_extras.parsers.mdx.grouped_source and
    # sybil_extras.parsers.myst.grouped_source.
    from sybil_extras.parsers.rest.grouped_source import GroupedSourceParser


    def evaluator(example: Example) -> None:
        """Evaluate the code block by printing it."""
        sys.stdout.write(example.parsed)


    group_parser = GroupedSourceParser(
        directive="group",
        evaluator=evaluator,
        # Pad the groups with newlines so that the
        # line number differences between blocks in the output match the
        # line number differences in the source document.
        # This is useful for error messages that reference line numbers.
        # However, this is detrimental to commands that expect the file
        # to not have a bunch of newlines in it, such as formatters.
        pad_groups=True,
    )
    code_block_parser = PythonCodeBlockParser()

    sybil = Sybil(parsers=[code_block_parser, group_parser])

    document = sybil.parse(path=Path("CHANGELOG.rst"))

    for item in document.examples():
        # One evaluate call will evaluate a code block with the contents of all
        # code blocks in the group.
        item.evaluate()

This makes Sybil act as though all of the code blocks within a group are a single code block,
to be evaluated with the ``evaluator`` given to ``GroupedSourceParser``.

Only code blocks parsed by another parser in the same Sybil instance will be grouped.

A group is defined by a pair of comments, ``group: start`` and ``group: end``.
The ``group: end`` example is expanded to include the contents of the code blocks in the group.

A reStructuredText example:

.. code-block:: rst

   .. code-block:: python

      """Code block outside the group."""

      x = 1
      assert x == 1

   .. group: start

   .. code-block:: python

       """Define a function to use in the next code block."""

       import sys


       def hello() -> None:
           """Print a greeting."""
           sys.stdout.write("Hello, world!")


       hello()

   .. code-block:: python

       """Run a function which is defined in the previous code block."""

       # We don't run ``hello()`` yet - ``doccmd`` does not support groups

   .. group: end

GroupAllParser
^^^^^^^^^^^^^^

.. code-block:: python

    """Use GroupAllParser to group all code blocks in a document."""

    import sys
    from pathlib import Path

    from sybil import Sybil
    from sybil.example import Example
    from sybil.parsers.rest.codeblock import PythonCodeBlockParser

    # Similar parsers are available at
    # sybil_extras.parsers.markdown.group_all,
    # sybil_extras.parsers.mdx.group_all and
    # sybil_extras.parsers.myst.group_all.
    from sybil_extras.parsers.rest.group_all import GroupAllParser


    def evaluator(example: Example) -> None:
        """Evaluate the code block by printing it."""
        sys.stdout.write(example.parsed)


    group_all_parser = GroupAllParser(
        evaluator=evaluator,
        # Pad the groups with newlines so that the
        # line number differences between blocks in the output match the
        # line number differences in the source document.
        # This is useful for error messages that reference line numbers.
        # However, this is detrimental to commands that expect the file
        # to not have a bunch of newlines in it, such as formatters.
        pad_groups=True,
    )
    code_block_parser = PythonCodeBlockParser()

    sybil = Sybil(parsers=[code_block_parser, group_all_parser])

    document = sybil.parse(path=Path("CHANGELOG.rst"))

    for item in document.examples():
        # One evaluate call will evaluate a code block with the contents of all
        # code blocks in the document.
        item.evaluate()

This makes Sybil act as though all of the code blocks in a document are a single code block,
to be evaluated with the ``evaluator`` given to ``GroupAllParser``.

Unlike ``GroupedSourceParser``, this parser does not require any special markup directives like ``group: start`` and ``group: end``.
All code blocks in the document are automatically grouped together.

Only code blocks parsed by another parser in the same Sybil instance will be grouped.

AttributeGroupedSourceParser
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The ``AttributeGroupedSourceParser`` groups MDX code blocks by their ``group`` attribute value, following Docusaurus conventions.
This is useful for MDX documentation where code blocks with the same group attribute should be combined and evaluated together.

.. code-block:: python

    """Use AttributeGroupedSourceParser to group MDX code blocks by attribute."""

    import sys
    from pathlib import Path

    from sybil import Sybil
    from sybil.example import Example

    from sybil_extras.evaluators.no_op import NoOpEvaluator
    from sybil_extras.parsers.mdx.attribute_grouped_source import (
        AttributeGroupedSourceParser,
    )
    from sybil_extras.parsers.mdx.codeblock import CodeBlockParser


    def evaluator(example: Example) -> None:
        """Evaluate the code block by printing it."""
        sys.stdout.write(example.parsed)


    code_block_parser = CodeBlockParser(language="python")
    group_parser = AttributeGroupedSourceParser(
        code_block_parser=code_block_parser,
        evaluator=evaluator,
        # The attribute name to use for grouping (default: "group")
        attribute_name="group",
        # Pad the groups with newlines so that the
        # line number differences between blocks in the output match the
        # line number differences in the source document.
        # This is useful for error messages that reference line numbers.
        # However, this is detrimental to commands that expect the file
        # to not have a bunch of newlines in it, such as formatters.
        pad_groups=True,
        # The evaluator to use for code blocks that don't have the
        # grouping attribute.
        ungrouped_evaluator=NoOpEvaluator(),
    )

    sybil = Sybil(parsers=[group_parser])

    document = sybil.parse(path=Path("example.mdx"))

    for item in document.examples():
        # One evaluate call will evaluate a code block with the contents of all
        # code blocks in the same group.
        item.evaluate()

This makes Sybil act as though all code blocks with the same ``group`` attribute value are a single code block,
to be evaluated with the ``evaluator`` given to ``AttributeGroupedSourceParser``.

An MDX example:

.. code-block:: markdown

   ```python group="example1"
   from pprint import pp
   ```

   Some text in between.

   ```python group="example1"
   pp({"hello": "world"})
   ```

   ```python group="example2"
   x = 1
   ```

In this example, the first two code blocks will be combined and evaluated as one block,
while the third block (with ``group="example2"``) will be evaluated separately.

Code blocks with the ``group`` attribute (or custom attribute name) will be grouped.
Code blocks without the attribute are evaluated with the ``ungrouped_evaluator``.

SphinxJinja2Parser
^^^^^^^^^^^^^^^^^^

Use the ``SphinxJinja2Parser`` to parse `sphinx-jinja2 <https://sphinx-jinja2.readthedocs.io/en/latest/>`_ templates in Sphinx documentation.

This extracts the source, arguments and options from ``.. jinja::`` directive blocks in reStructuredText documents or ``\`\`\`{jinja}`` blocks in MyST documents.

.. code-block:: python

    """Use SphinxJinja2Parser to extract Jinja templates."""

    from pathlib import Path

    from sybil import Sybil
    from sybil.example import Example

    # A similar parser is available at sybil_extras.parsers.myst.sphinx_jinja2.
    # There are no Markdown or MDX parsers as Sphinx is not used with them
    # without MyST.
    from sybil_extras.parsers.rest.sphinx_jinja2 import SphinxJinja2Parser


    def _evaluator(example: Example) -> None:
        """Check that the example is long enough."""
        minimum_length = 50
        assert len(example.parsed) >= minimum_length


    parser = SphinxJinja2Parser(evaluator=_evaluator)
    sybil = Sybil(parsers=[parser])
    document = sybil.parse(path=Path("CHANGELOG.rst"))
    for item in document.examples():
        item.evaluate()

Djot code block parser
^^^^^^^^^^^^^^^^^^^^^^

The djot ``CodeBlockParser`` correctly handles code blocks that are implicitly
closed when their parent container ends, following the
`djot specification <https://htmlpreview.github.io/?https://github.com/jgm/djot/blob/master/doc/syntax.html#code-block>`_.

For example, a code block inside a blockquote without a closing fence:

.. code-block:: text

   > ```python
   > code in a
   > block quote

   Paragraph.

.. code-block:: python

    """Use the djot CodeBlockParser for djot documents."""

    from sybil import Sybil

    from sybil_extras.evaluators.no_op import NoOpEvaluator
    from sybil_extras.parsers.djot.codeblock import CodeBlockParser

    parser = CodeBlockParser(language="python", evaluator=NoOpEvaluator())
    sybil = Sybil(parsers=[parser])

    pytest_collect_file = sybil.pytest()

Djot directive lexer
^^^^^^^^^^^^^^^^^^^^

Use ``DirectiveInDjotCommentLexer`` to extract directive information from djot
comments such as ``{% group: start %}``. This pairs well with
``sybil.testing.check_lexer`` for concise lexer tests.

.. code-block:: python

    """Lex djot directives and test them with check_lexer."""

    from sybil.testing import check_lexer

    from sybil_extras.parsers.djot.lexers import DirectiveInDjotCommentLexer

    lexer = DirectiveInDjotCommentLexer(directive="group", arguments=r".+")

    check_lexer(
        lexer=lexer,
        source_text="Before\n{% group: start %}\nAfter\n",
        expected_text="{% group: start %}",
        expected_lexemes={"directive": "group", "arguments": "start"},
    )

Markup Languages
----------------

The ``languages`` module provides a ``MarkupLanguage`` dataclass and predefined instances for working with different markup formats.
This is useful for building tools that need to work consistently across multiple markup languages.

.. code-block:: python

    """Use MarkupLanguage to work with different markup formats."""

    from pathlib import Path

    from sybil import Sybil

    from sybil_extras.evaluators.no_op import NoOpEvaluator
    from sybil_extras.languages import (
        DJOT,
        MARKDOWN,
        MDX,
        MYST,
        MYST_PERCENT_COMMENTS,
        NORG,
        RESTRUCTUREDTEXT,
    )

    assert MYST.name == "MyST"
    assert MYST_PERCENT_COMMENTS.name == "MyST (percent comments)"
    assert MARKDOWN.name == "Markdown"
    assert MDX.name == "MDX"
    assert DJOT.name == "Djot"
    assert NORG.name == "Norg"
    assert RESTRUCTUREDTEXT.name == "reStructuredText"

    code_parser = RESTRUCTUREDTEXT.code_block_parser_cls(
        language="python",
        evaluator=NoOpEvaluator(),
    )

    sybil = Sybil(parsers=[code_parser])
    document = sybil.parse(path=Path("README.rst"))

    for example in document.examples():
        example.evaluate()

.. |Build Status| image:: https://github.com/adamtheturtle/sybil-extras/actions/workflows/ci.yml/badge.svg?branch=main
   :target: https://github.com/adamtheturtle/sybil-extras/actions
.. |PyPI| image:: https://badge.fury.io/py/sybil-extras.svg
   :target: https://badge.fury.io/py/sybil-extras
