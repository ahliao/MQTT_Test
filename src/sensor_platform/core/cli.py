"""Shared command-line helpers for sensor platform services."""

from __future__ import annotations

import argparse

from sensor_platform.config import DEFAULT_CHANNEL, DEFAULT_SENSOR_ID, MQTT_HOST, MQTT_PORT

LOG_LEVEL_CHOICES = ("DEBUG", "INFO", "WARNING", "ERROR")


def add_mqtt_arguments(parser: argparse.ArgumentParser) -> None:
    """Add common MQTT broker options to a service parser."""
    parser.add_argument("--mqtt-host", default=MQTT_HOST)
    parser.add_argument("--mqtt-port", type=int, default=MQTT_PORT)


def add_sensor_identity_arguments(
    parser: argparse.ArgumentParser,
    *,
    default_sensor_id: str = DEFAULT_SENSOR_ID,
) -> None:
    """Add common sensor identity options to a service parser."""
    parser.add_argument("--sensor-id", default=default_sensor_id)
    parser.add_argument("--channel", type=int, default=DEFAULT_CHANNEL)


def add_logging_arguments(parser: argparse.ArgumentParser) -> None:
    """Add a common logging verbosity option to a service parser."""
    parser.add_argument("--log-level", default="INFO", choices=LOG_LEVEL_CHOICES)


def require_positive_float(value: float, option_name: str) -> None:
    """Stop startup when a numeric option that must be positive is invalid."""
    if value <= 0:
        raise SystemExit(f"{option_name} must be greater than 0")


def require_positive_int(value: int, option_name: str) -> None:
    """Stop startup when an integer option that must be positive is invalid."""
    if value <= 0:
        raise SystemExit(f"{option_name} must be greater than 0")
