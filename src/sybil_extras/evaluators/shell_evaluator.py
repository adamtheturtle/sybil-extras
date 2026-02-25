"""An evaluator for running shell commands on example files."""

import contextlib
import platform
import subprocess
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Protocol, runtime_checkable

from beartype import beartype
from sybil import Example
from sybil.evaluators.python import pad

from sybil_extras.evaluators._subprocess_utils import (
    lstrip_newlines,
    run_command,
)
from sybil_extras.evaluators.code_block_writer import CodeBlockWriterEvaluator


@beartype
@runtime_checkable
class _ExampleModified(Protocol):
    """A protocol for a callback to run when an example is modified."""

    def __call__(
        self,
        *,
        example: Example,
        modified_example_content: str,
    ) -> None:
        """This function is called when an example is modified."""
        # We disable a pylint warning here because the ellipsis is required
        # for Pyright to recognize this as a protocol.
        ...  # pylint: disable=unnecessary-ellipsis


@beartype
@runtime_checkable
class SourcePreparer(Protocol):
    """Prepare source content from an example.

    Implementations extract the raw source string from an example's parsed
    content.  The returned string is then padded and written to a temporary
    file by the runner.
    """

    def __call__(
        self,
        *,
        example: Example,
    ) -> str:
        """Return the source string for the given example."""
        # We disable a pylint warning here because the ellipsis is required
        # for Pyright to recognize this as a protocol.
        ...  # pylint: disable=unnecessary-ellipsis


@beartype
class _NoOpSourcePreparer:
    """Return the example's parsed content as-is."""

    def __call__(self, *, example: Example) -> str:
        """Return the parsed content of the example."""
        return str(object=example.parsed)


_NOOP_SOURCE_PREPARER = _NoOpSourcePreparer()


@beartype
@runtime_checkable
class ResultTransformer(Protocol):
    """Transform the result content before it is written back.

    Implementations receive the formatted content (after padding has been
    stripped) and return the string that should replace the original code
    block in the document.
    """

    def __call__(
        self,
        *,
        content: str,
        example: Example,
    ) -> str:
        """Return the transformed content."""
        # We disable a pylint warning here because the ellipsis is required
        # for Pyright to recognize this as a protocol.
        ...  # pylint: disable=unnecessary-ellipsis


@beartype
class _NoOpResultTransformer:
    """Return the content unchanged."""

    def __call__(self, *, content: str, example: Example) -> str:
        """Return the content as-is."""
        del example
        return content


_NOOP_RESULT_TRANSFORMER = _NoOpResultTransformer()


@beartype
@runtime_checkable
class TempFilePathMaker(Protocol):
    """A protocol for creating temporary file paths for examples.

    This allows full customization of the temporary file path used when
    running shell commands on documentation examples.
    """

    def __call__(
        self,
        *,
        example: Example,
    ) -> Path:
        """Create a temporary file path for an example.

        Args:
            example: The Sybil example for which to create a file path.

        Returns:
            A Path object for the temporary file. The file should typically
            be created in the same directory as the source file
            (``example.path.parent``) so that relative imports and
            tool configurations work correctly.
        """
        # We disable a pylint warning here because the ellipsis is required
        # for Pyright to recognize this as a protocol.
        ...  # pylint: disable=unnecessary-ellipsis


@beartype
class _ShellCommandRunner:
    """
    Run a shell command on an example file (internal
    implementation).
    """

    def __init__(
        self,
        *,
        args: Sequence[str | Path],
        temp_file_path_maker: TempFilePathMaker,
        env: Mapping[str, str] | None = None,
        newline: str | None = None,
        pad_file: bool,
        write_to_file: bool,
        use_pty: bool,
        encoding: str | None = None,
        on_modify: _ExampleModified | None = None,
        namespace_key: str = "",
        source_preparer: SourcePreparer = _NOOP_SOURCE_PREPARER,
        result_transformer: ResultTransformer = _NOOP_RESULT_TRANSFORMER,
    ) -> None:
        """Initialize the shell command runner.

        Args:
            args: The shell command to run.
            temp_file_path_maker: A callable that generates the temporary
                file path for an example.
            env: The environment variables to use when running the shell
                command.
            newline: The newline string to use for the temporary file.
            pad_file: Whether to pad the file with newlines at the start.
            write_to_file: Whether to write changes to the file.
            use_pty: Whether to use a pseudo-terminal for running commands.
            encoding: The encoding to use for the temporary file.
            on_modify: A callback to run when the example is modified.
            namespace_key: The key to store modified content in the namespace.
            source_preparer: A callable that extracts source from an example.
            result_transformer: A callable that transforms the result before
                it is written back.
        """
        self._args = args
        self._env = env
        self._pad_file = pad_file
        self._temp_file_path_maker = temp_file_path_maker
        self._write_to_file = write_to_file
        self._newline = newline
        self._use_pty = use_pty
        self._encoding = encoding
        self._on_modify = on_modify
        self._namespace_key = namespace_key
        self._source_preparer = source_preparer
        self._result_transformer = result_transformer

    def __call__(self, example: Example) -> None:
        """Run the shell command on the example file."""
        if (
            self._use_pty and platform.system() == "Windows"
        ):  # pragma: no cover
            msg = "Pseudo-terminal not supported on Windows."
            raise ValueError(msg)

        padding_line = (
            example.line + example.parsed.line_offset if self._pad_file else 0
        )

        raw_source = self._source_preparer(example=example)
        source = pad(source=raw_source, line=padding_line)
        temp_file = self._temp_file_path_maker(example=example)

        # The parsed code block at the end of a file is given without a
        # trailing newline.  Some tools expect that a file has a trailing
        # newline.  This is especially true for formatters.  We add a
        # newline to the end of the file if it is missing.
        new_source = source + "\n" if not source.endswith("\n") else source
        temp_file.write_text(
            data=new_source,
            encoding=self._encoding,
            newline=self._newline,
        )

        temp_file_content = ""
        try:
            result = run_command(
                command=[
                    str(object=item) for item in [*self._args, temp_file]
                ],
                env=self._env,
                use_pty=self._use_pty,
            )

            with contextlib.suppress(FileNotFoundError):
                temp_file_content = temp_file.read_text(
                    encoding=self._encoding
                )
        finally:
            with contextlib.suppress(FileNotFoundError):
                temp_file.unlink()

        if new_source != temp_file_content and self._on_modify is not None:
            self._on_modify(
                example=example,
                modified_example_content=temp_file_content,
            )

        if self._write_to_file:
            # Examples are given with no leading newline.
            # While it is possible that a formatter added leading newlines,
            # we assume that this is not the case, and we remove any leading
            # newlines from the replacement which were added by the padding.
            new_region_content = lstrip_newlines(
                input_string=temp_file_content,
                number_of_newlines=padding_line,
            )
            new_region_content = self._result_transformer(
                content=new_region_content,
                example=example,
            )
            example.document.namespace[self._namespace_key] = (
                new_region_content
            )

        if result.returncode != 0:
            raise subprocess.CalledProcessError(
                cmd=result.args,
                returncode=result.returncode,
                output=result.stdout,
                stderr=result.stderr,
            )


@beartype
class ShellCommandEvaluator:
    """Run a shell command on the example file."""

    def __init__(
        self,
        *,
        args: Sequence[str | Path],
        temp_file_path_maker: TempFilePathMaker,
        env: Mapping[str, str] | None = None,
        newline: str | None = None,
        # For some commands, padding is good: e.g. we want to see the error
        # reported on the correct line for `mypy`. For others, padding is bad:
        # e.g. `ruff format` expects the file to be formatted without a bunch
        # of newlines at the start.
        pad_file: bool,
        write_to_file: bool,
        use_pty: bool,
        encoding: str | None = None,
        on_modify: _ExampleModified | None = None,
    ) -> None:
        """Initialize the evaluator.

        Args:
            args: The shell command to run.
            temp_file_path_maker: A callable that generates the temporary
                file path for an example. The callable receives the example
                and should return a Path for the temporary file.
            env: The environment variables to use when running the shell
                command.
            newline: The newline string to use for the temporary file.
                If ``None``, use the system default.
            pad_file: Whether to pad the file with newlines at the start.
                This is useful for error messages that report the line number.
                However, this is detrimental to commands that expect the file
                to not have a bunch of newlines at the start, such as
                formatters.
            write_to_file: Whether to write changes to the file. This is useful
                for formatters.
            use_pty: Whether to use a pseudo-terminal for running commands.
                This can be useful e.g. to get color output, but can also break
                in some environments. Not supported on Windows.
            encoding: The encoding to use reading documents which include a
                given example, and for the temporary file. If ``None``,
                use the system default.
            on_modify: A callback to run when the example is modified by the
                evaluator.

        Raises:
            ValueError: If pseudo-terminal is requested on Windows.
        """
        namespace_key = "_shell_evaluator_modified_content"
        runner = _ShellCommandRunner(
            args=args,
            temp_file_path_maker=temp_file_path_maker,
            env=env,
            newline=newline,
            pad_file=pad_file,
            write_to_file=write_to_file,
            use_pty=use_pty,
            encoding=encoding,
            on_modify=on_modify,
            namespace_key=namespace_key,
        )
        self._evaluator: _ShellCommandRunner | CodeBlockWriterEvaluator
        if write_to_file:
            self._evaluator = CodeBlockWriterEvaluator(
                evaluator=runner,
                namespace_key=namespace_key,
                encoding=encoding,
            )
        else:
            self._evaluator = runner

    def __call__(self, example: Example) -> None:
        """Run the shell command on the example file."""
        self._evaluator(example)
