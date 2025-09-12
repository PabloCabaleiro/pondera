from __future__ import annotations

import logging


def test_logger_available() -> None:
    log = logging.getLogger("pondera")
    # Should return a Logger instance; no strict level expectations.
    assert log.name == "pondera"
