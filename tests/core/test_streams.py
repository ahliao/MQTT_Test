"""Tests for shared MQTT/protobuf stream registry metadata."""

from __future__ import annotations

import pytest

from sensor_platform.config import (
    HIGH_RATE_PROCESSOR_RESULTS_TOPIC,
    HIGH_RATE_SENSOR_BATCHES_TOPIC,
    PROCESSOR_RESULTS_TOPIC,
    SENSOR_READINGS_TOPIC,
)
from sensor_platform.streams import (
    HIGH_RATE_PROCESSED_ADC_STREAM,
    HIGH_RATE_RAW_ADC_STREAM,
    PROCESSED_ADC_STREAM,
    RAW_ADC_STREAM,
    STREAMS,
    StreamKind,
    default_visible_streams,
    get_stream,
    get_stream_by_topic,
)


def test_streams_have_unique_names_and_topics() -> None:
    names = [stream.name for stream in STREAMS]
    topics = [stream.topic for stream in STREAMS]

    assert len(names) == len(set(names))
    assert len(topics) == len(set(topics))


def test_streams_include_current_topics() -> None:
    streams_by_name = {stream.name: stream for stream in STREAMS}

    assert streams_by_name[RAW_ADC_STREAM].topic == SENSOR_READINGS_TOPIC
    assert streams_by_name[PROCESSED_ADC_STREAM].topic == PROCESSOR_RESULTS_TOPIC
    assert streams_by_name[HIGH_RATE_RAW_ADC_STREAM].topic == HIGH_RATE_SENSOR_BATCHES_TOPIC
    assert streams_by_name[HIGH_RATE_PROCESSED_ADC_STREAM].topic == HIGH_RATE_PROCESSOR_RESULTS_TOPIC


def test_streams_have_callable_parsers() -> None:
    for stream in STREAMS:
        assert callable(stream.parser)


def test_lookup_by_name_and_topic() -> None:
    stream = get_stream(RAW_ADC_STREAM)

    assert stream.kind == StreamKind.LOW_RATE_RAW
    assert get_stream_by_topic(stream.topic) == stream


def test_unknown_lookups_raise_clear_errors() -> None:
    with pytest.raises(KeyError, match="Unknown stream name: missing"):
        get_stream("missing")

    with pytest.raises(KeyError, match="Unknown stream topic: missing/topic"):
        get_stream_by_topic("missing/topic")


def test_default_visible_streams_exclude_raw_high_rate_batches() -> None:
    visible_names = {stream.name for stream in default_visible_streams()}

    assert RAW_ADC_STREAM in visible_names
    assert PROCESSED_ADC_STREAM in visible_names
    assert HIGH_RATE_PROCESSED_ADC_STREAM in visible_names
    assert HIGH_RATE_RAW_ADC_STREAM not in visible_names
