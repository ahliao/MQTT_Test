"""Time helpers keep timestamp units explicit across the project."""

from __future__ import annotations

import time


def now_ms() -> int:
    """Return the current Unix timestamp in milliseconds."""
    return int(time.time() * 1000)


def now_us() -> int:
    """Return the current Unix timestamp in microseconds."""
    return time.time_ns() // 1_000
