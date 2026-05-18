"""Tests for protobuf serialization and parse error handling."""

from __future__ import annotations

import pytest

from sensor_platform.generated import sensor_platform_pb2
from sensor_platform.core.protobuf_helpers import parse_adc_reading, serialize_message


def test_adc_reading_round_trip() -> None:
    # Round-trip tests confirm the generated protobuf class and helper agree.
    original = sensor_platform_pb2.AdcReading(
        sensor_id="test-sensor",
        timestamp_ms=123456789,
        channel=1,
        raw_value=2048,
        voltage=1.65,
    )

    parsed = parse_adc_reading(serialize_message(original))

    assert parsed == original


def test_parse_adc_reading_rejects_invalid_payload() -> None:
    with pytest.raises(ValueError):
        parse_adc_reading(b"not protobuf")
