"""Tests for GUI stream configuration metadata."""

from __future__ import annotations

from sensor_platform.config import (
    HIGH_RATE_PROCESSOR_RESULTS_TOPIC,
    PROCESSOR_RESULTS_TOPIC,
    SENSOR_READINGS_TOPIC,
)
from sensor_platform.gui.config import (
    GUI_STREAMS,
    HIGH_RATE_PROCESSED_ADC_STREAM,
    PROCESSED_ADC_STREAM,
    RAW_ADC_STREAM,
)


def test_gui_streams_have_unique_names_and_topics() -> None:
    names = [stream.name for stream in GUI_STREAMS]
    topics = [stream.topic for stream in GUI_STREAMS]

    assert len(names) == len(set(names))
    assert len(topics) == len(set(topics))


def test_gui_streams_include_current_monitor_topics() -> None:
    streams_by_name = {stream.name: stream for stream in GUI_STREAMS}

    assert streams_by_name[RAW_ADC_STREAM].topic == SENSOR_READINGS_TOPIC
    assert streams_by_name[PROCESSED_ADC_STREAM].topic == PROCESSOR_RESULTS_TOPIC
    assert streams_by_name[HIGH_RATE_PROCESSED_ADC_STREAM].topic == HIGH_RATE_PROCESSOR_RESULTS_TOPIC
