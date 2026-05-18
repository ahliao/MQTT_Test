"""Configuration describing which MQTT/protobuf streams the GUI monitors."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from google.protobuf.message import Message

from sensor_platform.config import (
    HIGH_RATE_PROCESSOR_RESULTS_TOPIC,
    PROCESSOR_RESULTS_TOPIC,
    SENSOR_READINGS_TOPIC,
)
from sensor_platform.core.protobuf_helpers import (
    parse_adc_reading,
    parse_processed_reading,
    parse_processed_sample_batch,
)


# Stable names let the MQTT worker and GUI agree on what kind of message arrived.
RAW_ADC_STREAM = "raw_adc"
PROCESSED_ADC_STREAM = "processed_adc"
HIGH_RATE_PROCESSED_ADC_STREAM = "high_rate_processed_adc"


@dataclass(frozen=True)
class GuiStreamConfig:
    """One MQTT topic plus the parser and display metadata for that topic."""

    name: str
    display_name: str
    topic: str
    parser: Callable[[bytes], Message]
    stream_kind: str


GUI_STREAMS = [
    GuiStreamConfig(
        name=RAW_ADC_STREAM,
        display_name="Low-rate raw ADC readings",
        topic=SENSOR_READINGS_TOPIC,
        parser=parse_adc_reading,
        stream_kind="low_rate_raw",
    ),
    GuiStreamConfig(
        name=PROCESSED_ADC_STREAM,
        display_name="Low-rate processed ADC readings",
        topic=PROCESSOR_RESULTS_TOPIC,
        parser=parse_processed_reading,
        stream_kind="low_rate_processed",
    ),
    GuiStreamConfig(
        name=HIGH_RATE_PROCESSED_ADC_STREAM,
        display_name="High-rate processed ADC batches",
        topic=HIGH_RATE_PROCESSOR_RESULTS_TOPIC,
        parser=parse_processed_sample_batch,
        stream_kind="high_rate_processed_batch",
    ),
]
