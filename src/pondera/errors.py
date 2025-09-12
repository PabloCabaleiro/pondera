"""Centralized structured exception hierarchy for Pondera.

The goal is to provide a small, well‑named set of error types that user code
and tests can depend on without needing to pattern‑match arbitrary underlying
exceptions raised by dependencies (asyncio, pydantic, yaml, etc.).

Design:
  - PonderaError is the common base (subclass of RuntimeError for ergonomics).
  - TimeoutError also inherits from ``asyncio.TimeoutError`` so existing code
    catching that builtin still works while gaining the structured variant.
  - RunnerError / JudgeError signal failures inside user‑provided runner /
    judge implementations (normalization, config, execution issues).
  - ValidationError is raised for user facing spec / YAML / schema problems.
"""

from __future__ import annotations

import asyncio

__all__ = [
    "PonderaError",
    "RunnerError",
    "JudgeError",
    "TimeoutError",
    "ValidationError",
]


class PonderaError(RuntimeError):
    """Base class for all structured Pondera errors."""


class TimeoutError(asyncio.TimeoutError, PonderaError):
    """Operation exceeded the configured timeout.

    Subclasses ``asyncio.TimeoutError`` for backward compatibility with existing
    ``pytest.raises(asyncio.TimeoutError)`` style expectations.
    """


class RunnerError(PonderaError):
    """Raised when a runner cannot execute or its output cannot be normalized."""


class JudgeError(PonderaError):
    """Raised for judge configuration or runtime errors."""


class ValidationError(PonderaError):
    """Raised for user / content validation issues (YAML, schema, thresholds)."""
