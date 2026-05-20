"""Shared MQTT/protobuf stream registry.

The registry is the project-level source of truth for known MQTT topics and
their protobuf parsers. Display layers can filter this metadata for their own
needs without redefining topic/parser pairs.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum

from google.protobuf.message import Message

from sensor_platform.config import (
    HIGH_RATE_PROCESSOR_RESULTS_TOPIC,
    HIGH_RATE_SENSOR_BATCHES_TOPIC,
    PROCESSOR_RESULTS_TOPIC,
    SENSOR_READINGS_TOPIC,
)
from sensor_platform.core.protobuf_helpers import (
    parse_adc_reading,
    parse_adc_sample_batch,
    parse_processed_reading,
    parse_processed_sample_batch,
)


# Stable names let services and displays agree on which decoded stream arrived.
RAW_ADC_STREAM = "raw_adc"
PROCESSED_ADC_STREAM = "processed_adc"
HIGH_RATE_RAW_ADC_STREAM = "high_rate_raw_adc"
HIGH_RATE_PROCESSED_ADC_STREAM = "high_rate_processed_adc"


class StreamKind(StrEnum):
    """Broad stream categories used by monitors and future display panels."""

    LOW_RATE_RAW = "low_rate_raw"
    LOW_RATE_PROCESSED = "low_rate_processed"
    HIGH_RATE_RAW_BATCH = "high_rate_raw_batch"
    HIGH_RATE_PROCESSED_BATCH = "high_rate_processed_batch"


@dataclass(frozen=True)
class StreamConfig:
    """One known MQTT topic plus its protobuf parser and display metadata."""

    name: str
    display_name: str
    topic: str
    parser: Callable[[bytes], Message]
    kind: StreamKind
    default_visible: bool = True

    @property
    def stream_kind(self) -> str:
        """Compatibility alias for existing GUI code and tests."""
        return self.kind.value


STREAMS = (
    StreamConfig(
        name=RAW_ADC_STREAM,
        display_name="Low-rate raw ADC readings",
        topic=SENSOR_READINGS_TOPIC,
        parser=parse_adc_reading,
        kind=StreamKind.LOW_RATE_RAW,
    ),
    StreamConfig(
        name=PROCESSED_ADC_STREAM,
        display_name="Low-rate processed ADC readings",
        topic=PROCESSOR_RESULTS_TOPIC,
        parser=parse_processed_reading,
        kind=StreamKind.LOW_RATE_PROCESSED,
    ),
    StreamConfig(
        name=HIGH_RATE_RAW_ADC_STREAM,
        display_name="High-rate raw ADC batches",
        topic=HIGH_RATE_SENSOR_BATCHES_TOPIC,
        parser=parse_adc_sample_batch,
        kind=StreamKind.HIGH_RATE_RAW_BATCH,
        default_visible=False,
    ),
    StreamConfig(
        name=HIGH_RATE_PROCESSED_ADC_STREAM,
        display_name="High-rate processed ADC batches",
        topic=HIGH_RATE_PROCESSOR_RESULTS_TOPIC,
        parser=parse_processed_sample_batch,
        kind=StreamKind.HIGH_RATE_PROCESSED_BATCH,
    ),
)


def streams_by_name() -> dict[str, StreamConfig]:
    """Return stream metadata keyed by stable stream name."""
    return {stream.name: stream for stream in STREAMS}


def streams_by_topic() -> dict[str, StreamConfig]:
    """Return stream metadata keyed by MQTT topic."""
    return {stream.topic: stream for stream in STREAMS}


def get_stream(name: str) -> StreamConfig:
    """Look up a stream by stable name."""
    try:
        return streams_by_name()[name]
    except KeyError as exc:
        raise KeyError(f"Unknown stream name: {name}") from exc


def get_stream_by_topic(topic: str) -> StreamConfig:
    """Look up a stream by MQTT topic."""
    try:
        return streams_by_topic()[topic]
    except KeyError as exc:
        raise KeyError(f"Unknown stream topic: {topic}") from exc


def default_visible_streams() -> list[StreamConfig]:
    """Return streams that monitors should subscribe to by default."""
    return [stream for stream in STREAMS if stream.default_visible]
