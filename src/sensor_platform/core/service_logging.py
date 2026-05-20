"""Shared logging setup for sensor platform services."""

from __future__ import annotations

import logging


def configure_logging(level: str) -> None:
    """Configure standard service logging with a consistent format."""
    logging.basicConfig(
        level=getattr(logging, level),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
