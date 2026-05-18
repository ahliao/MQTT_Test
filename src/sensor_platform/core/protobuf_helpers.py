"""Small helpers that keep protobuf byte handling in one place."""

from __future__ import annotations

from google.protobuf.message import DecodeError, Message

from sensor_platform.generated import sensor_platform_pb2


def serialize_message(message: Message) -> bytes:
    """Serialize any protobuf message to bytes for MQTT publishing."""
    return message.SerializeToString()


def parse_adc_reading(payload: bytes) -> sensor_platform_pb2.AdcReading:
    """Parse MQTT bytes into a low-rate raw ADC reading."""
    reading = sensor_platform_pb2.AdcReading()
    _parse_into(reading, payload)
    return reading


def parse_processed_reading(payload: bytes) -> sensor_platform_pb2.ProcessedReading:
    """Parse MQTT bytes into a low-rate processed reading."""
    reading = sensor_platform_pb2.ProcessedReading()
    _parse_into(reading, payload)
    return reading


def parse_adc_sample_batch(payload: bytes) -> sensor_platform_pb2.AdcSampleBatch:
    """Parse MQTT bytes into a high-rate raw sample batch."""
    batch = sensor_platform_pb2.AdcSampleBatch()
    _parse_into(batch, payload)
    return batch


def parse_processed_sample_batch(payload: bytes) -> sensor_platform_pb2.ProcessedSampleBatch:
    """Parse MQTT bytes into a high-rate processed batch summary."""
    batch = sensor_platform_pb2.ProcessedSampleBatch()
    _parse_into(batch, payload)
    return batch


def _parse_into(message: Message, payload: bytes) -> None:
    """Use a common parser so decode errors become friendly ValueError messages."""
    try:
        message.ParseFromString(payload)
    except DecodeError as exc:
        raise ValueError("MQTT payload was not a valid protobuf message") from exc
