"""Lightweight logging helpers for Pondera.

Centralizes acquisition and one‑time configuration of the framework logger.
We intentionally keep this minimal (standard library only) and avoid any
over‑engineering so host applications can further customize logging if they
wish (handlers / formatters / propagation).
"""

from __future__ import annotations

import logging
from typing import Any

LOGGER_NAME = "pondera"
_configured = False


def get_logger() -> logging.Logger:
    """Return the shared framework logger."""
    return logging.getLogger(LOGGER_NAME)


def configure_logging(level: str | None = None, *, force: bool = False, **extra: Any) -> None:
    """Configure the pondera logger once.

    If the logger already has handlers attached we assume the embedding
    application configured logging and we only adjust the level (unless
    ``force`` is True).
    """
    global _configured
    logger = get_logger()
    if not force and _configured:
        if level:
            logger.setLevel(level.upper())
        return
    if level:
        logger.setLevel(level.upper())
    if not logger.handlers or force:
        # Basic stream handler with concise format.
        h = logging.StreamHandler()
        fmt = extra.get(
            "format",
            "%(asctime)s %(levelname)s %(name)s: %(message)s",
        )
        datefmt = extra.get("datefmt", "%H:%M:%S")
        h.setFormatter(logging.Formatter(fmt=fmt, datefmt=datefmt))
        if force:
            logger.handlers.clear()
        logger.addHandler(h)
    logger.propagate = False  # Avoid duplicate lines if root configured.
    _configured = True
