"""Tests for shared command-line helper functions."""

from __future__ import annotations

import argparse

import pytest

from sensor_platform.config import DEFAULT_CHANNEL, DEFAULT_SENSOR_ID, MQTT_HOST, MQTT_PORT
from sensor_platform.core.cli import (
    LOG_LEVEL_CHOICES,
    add_logging_arguments,
    add_mqtt_arguments,
    add_sensor_identity_arguments,
    require_positive_float,
    require_positive_int,
)


def test_add_mqtt_arguments_uses_project_defaults() -> None:
    parser = argparse.ArgumentParser()

    add_mqtt_arguments(parser)
    args = parser.parse_args([])

    assert args.mqtt_host == MQTT_HOST
    assert args.mqtt_port == MQTT_PORT


def test_add_mqtt_arguments_accepts_overrides() -> None:
    parser = argparse.ArgumentParser()

    add_mqtt_arguments(parser)
    args = parser.parse_args(["--mqtt-host", "192.168.1.50", "--mqtt-port", "1884"])

    assert args.mqtt_host == "192.168.1.50"
    assert args.mqtt_port == 1884


def test_add_sensor_identity_arguments_uses_defaults() -> None:
    parser = argparse.ArgumentParser()

    add_sensor_identity_arguments(parser)
    args = parser.parse_args([])

    assert args.sensor_id == DEFAULT_SENSOR_ID
    assert args.channel == DEFAULT_CHANNEL


def test_add_sensor_identity_arguments_accepts_custom_default_sensor_id() -> None:
    parser = argparse.ArgumentParser()

    add_sensor_identity_arguments(parser, default_sensor_id="custom-sensor")
    args = parser.parse_args([])

    assert args.sensor_id == "custom-sensor"


def test_add_logging_arguments_uses_info_default() -> None:
    parser = argparse.ArgumentParser()

    add_logging_arguments(parser)
    args = parser.parse_args([])

    assert args.log_level == "INFO"
    assert "DEBUG" in LOG_LEVEL_CHOICES


def test_positive_float_validation_accepts_positive_values() -> None:
    require_positive_float(0.1, "--rate")


@pytest.mark.parametrize("value", [0.0, -1.0])
def test_positive_float_validation_rejects_non_positive_values(value: float) -> None:
    with pytest.raises(SystemExit, match="--rate must be greater than 0"):
        require_positive_float(value, "--rate")


def test_positive_int_validation_accepts_positive_values() -> None:
    require_positive_int(1, "--count")


@pytest.mark.parametrize("value", [0, -1])
def test_positive_int_validation_rejects_non_positive_values(value: int) -> None:
    with pytest.raises(SystemExit, match="--count must be greater than 0"):
        require_positive_int(value, "--count")
