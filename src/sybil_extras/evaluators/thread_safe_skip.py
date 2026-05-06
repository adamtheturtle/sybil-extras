"""A thread-safe evaluator for ``skip`` directives.

Upstream :class:`sybil.evaluators.skip.Skipper` mutates per-document
state (``document_state`` / ``SkipState``) as examples are evaluated.
When examples from a single document are dispatched concurrently, those
mutations race and the resulting skip decisions become non-deterministic
(see https://github.com/simplistix/sybil/issues/166).

This module provides :class:`ThreadSafeSkipper`, an API-compatible
replacement that resolves skip decisions at parse time. Each non-skip
example is mapped to a single governing skip directive (if any) by
walking ``document.regions`` once under a per-document lock. Conditional
``if`` reasons are evaluated lazily, exactly once per directive, with
the result cached so concurrent evaluators all see the same decision.
"""

import builtins
import threading
from dataclasses import dataclass, field
from typing import Any
from unittest import SkipTest

from beartype import beartype
from sybil import Document, Example
from sybil.evaluators.skip import If, Skipper
from sybil.example import NotEvaluated
from sybil.region import Region

# ``eval`` has a positional-only signature in typeshed but is reported
# as "too many positional arguments" by this project's strict-kwargs
# mypy plugin. Going through an ``Any`` reference bypasses both
# checkers.
_eval: Any = builtins.eval


def _eval_in_namespace(*, source: str, namespace: dict[str, Any]) -> object:
    """Run :func:`eval` against ``namespace``.

    Wrapping ``eval`` keeps the call site confined here and exposes
    keyword-only parameters to callers.
    """
    return _eval(source, namespace)


def _make_skip(reason: object) -> SkipTest:
    """Build a :class:`unittest.SkipTest` carrying ``reason``.

    Typeshed declares ``SkipTest.__init__(self, reason: str)``, but at
    runtime the class only inherits ``BaseException.__init__``, which
    accepts a variadic ``*args``. Initializing via ``BaseException``
    avoids the typeshed/runtime mismatch and the project's
    strict-kwargs mypy plugin.
    """
    exception = SkipTest.__new__(SkipTest)
    BaseException.__init__(exception, reason)
    return exception


@dataclass
class _SkipDirective:
    """Resolved metadata about a ``skip`` directive in a document."""

    region: Region
    action: str
    reason: str | None
    sequence_error: ValueError | None = None
    decision: "_Decision | None" = None
    decision_lock: "threading.Lock" = field(
        default_factory=threading.Lock,
    )


@dataclass(frozen=True)
class _Decision:
    """Cached skip decision for a directive's governed examples.

    ``kind`` is one of:

    * ``"silent"`` - the example is silently skipped (no exception).
    * ``"raise"`` - the example is skipped by raising ``exception``.
    * ``"fall_through"`` - the directive does not apply (a conditional
      ``if`` evaluated falsy); the example evaluates normally.
    """

    kind: str
    exception: Exception | None = None


@dataclass
class _DocumentPlan:
    """Per-document skip plan built from regions in source order."""

    directive_for_region: dict[int, _SkipDirective] = field(
        default_factory=dict[int, _SkipDirective],
    )
    skip_directive_for_region: dict[int, _SkipDirective] = field(
        default_factory=dict[int, _SkipDirective],
    )


@beartype
class ThreadSafeSkipper(Skipper):
    """A thread-safe drop-in replacement for ``sybil``'s ``Skipper``.

    Subclasses :class:`sybil.evaluators.skip.Skipper` so it can be
    returned anywhere a ``Skipper`` is expected. The base class's
    ``document_state`` attribute is left in place but unused; all
    decisions are routed through this class's plan-based logic.
    """

    def __init__(self, directive: str) -> None:
        """
        Args:
            directive: The directive name (e.g. ``"skip"``).
        """
        super().__init__(directive=directive)
        self._plans: dict[Document, _DocumentPlan] = {}
        self._lock = threading.RLock()

    def _plan_for(self, document: Document) -> _DocumentPlan:
        """Return the plan for ``document``, building it under lock."""
        with self._lock:
            plan = self._plans.get(document)
            if plan is None:
                plan = self._build_plan(document=document)
                self._plans[document] = plan
            return plan

    def _validate_skip_action(
        self,
        *,
        action: str,
        reason: str | None,
        last_action: str | None,
    ) -> ValueError | None:
        """Return a sequence error for ``action``, or ``None`` if
        valid.
        """
        directive = self.directive
        if action not in ("start", "next", "end"):
            return ValueError("Bad skip action: " + action)
        if last_action is None and action not in ("start", "next"):
            return ValueError(
                f"'{directive}: {action}' must follow '{directive}: start'",
            )
        if last_action and action != "end":
            return ValueError(
                f"'{directive}: {action}' cannot follow "
                f"'{directive}: {last_action}'",
            )
        if action == "end" and reason:
            return ValueError("Cannot have condition on 'skip: end'")
        return None

    def _build_plan(self, document: Document) -> _DocumentPlan:
        """Walk ``document.regions`` and resolve each region's skip
        state.
        """
        plan = _DocumentPlan()
        last_action: str | None = None
        pending_next: _SkipDirective | None = None
        active_start: _SkipDirective | None = None

        for _, region in document.regions:
            if region.evaluator is not self:
                if pending_next is not None:
                    plan.directive_for_region[id(region)] = pending_next
                    pending_next = None
                    last_action = "start" if active_start is not None else None
                elif active_start is not None:
                    plan.directive_for_region[id(region)] = active_start
                continue

            action, reason = region.parsed
            entry = _SkipDirective(region=region, action=action, reason=reason)
            plan.skip_directive_for_region[id(region)] = entry
            entry.sequence_error = self._validate_skip_action(
                action=action,
                reason=reason,
                last_action=last_action,
            )
            if entry.sequence_error is not None:
                continue

            last_action = action
            if action == "next":
                pending_next = entry
            elif action == "start":
                active_start = entry
            else:
                # ``end`` cancels both an open ``start`` interval and
                # any pending ``next`` directive that has not yet been
                # consumed by a non-skip example, matching the upstream
                # ``Skipper.remove`` call which clears per-document
                # state.
                active_start = None
                pending_next = None
                last_action = None

        return plan

    def _resolve_decision(
        self, *, directive: _SkipDirective, document: Document
    ) -> _Decision:
        """Evaluate ``directive``'s reason against
        ``document.namespace``.
        """
        with directive.decision_lock:
            if directive.decision is not None:
                return directive.decision
            decision = self._compute_decision(
                directive=directive, document=document
            )
            directive.decision = decision
            return decision

    @staticmethod
    def _compute_decision(
        *, directive: _SkipDirective, document: Document
    ) -> _Decision:
        """Compute the decision for a directive without caching."""
        reason = directive.reason
        if not reason:
            return _Decision(kind="silent")

        namespace = document.namespace.copy()
        text = reason.lstrip()
        conditional = text.startswith("if")
        if conditional:
            condition = text[2:]
            text = "if_" + condition
            namespace["if_"] = If(default_reason=condition)
        result = _eval_in_namespace(source=text, namespace=namespace)
        if result:
            return _Decision(
                kind="raise",
                exception=_make_skip(reason=result),
            )
        return _Decision(kind="fall_through")

    def evaluate_skip_example(self, example: Example) -> None:
        """Validate the skip directive at ``example``'s region.

        Raises any sequence error detected at plan-build time, matching
        the message and ordering of upstream ``Skipper``.
        """
        plan = self._plan_for(document=example.document)
        entry = plan.skip_directive_for_region[id(example.region)]
        if entry.sequence_error is not None:
            raise entry.sequence_error

    def evaluate_other_example(self, example: Example) -> None:
        """Apply the resolved skip decision for a non-skip ``example``."""
        plan = self._plan_for(document=example.document)
        directive = plan.directive_for_region.get(id(example.region))
        if directive is None:
            raise NotEvaluated
        decision = self._resolve_decision(
            directive=directive, document=example.document
        )
        if decision.kind == "fall_through":
            raise NotEvaluated
        if decision.kind == "raise" and decision.exception is not None:
            raise decision.exception

    def __call__(self, example: Example) -> None:
        """Evaluate ``example`` against this skipper."""
        if example.region.evaluator is self:
            self.evaluate_skip_example(example=example)
        else:
            self.evaluate_other_example(example=example)
