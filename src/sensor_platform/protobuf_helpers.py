from __future__ import annotations

from google.protobuf.message import DecodeError, Message

from sensor_platform.generated import sensor_platform_pb2


def serialize_message(message: Message) -> bytes:
    """Serialize any protobuf message to bytes for MQTT publishing."""
    return message.SerializeToString()


def parse_adc_reading(payload: bytes) -> sensor_platform_pb2.AdcReading:
    reading = sensor_platform_pb2.AdcReading()
    _parse_into(reading, payload)
    return reading


def parse_processed_reading(payload: bytes) -> sensor_platform_pb2.ProcessedReading:
    reading = sensor_platform_pb2.ProcessedReading()
    _parse_into(reading, payload)
    return reading


def _parse_into(message: Message, payload: bytes) -> None:
    try:
        message.ParseFromString(payload)
    except DecodeError as exc:
        raise ValueError("MQTT payload was not a valid protobuf message") from exc
