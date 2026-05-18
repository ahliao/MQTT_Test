"""Tests for high-rate batching, summarization, and rolling plot history."""

from __future__ import annotations

import pytest

from sensor_platform.sensors.high_rate_batch import (
    batch_time_axis_seconds,
    generate_raw_batch,
    raw_values_to_voltages,
    summarize_batch,
)
from sensor_platform.gui.plot_history import HighRatePlotHistory


def test_generate_raw_batch_returns_requested_sample_count() -> None:
    # The waveform is random/noisy, so verify size and ADC range rather than exact values.
    values = generate_raw_batch(sample_count=100, sample_rate_hz=10_000, batch_index=0)

    assert len(values) == 100
    assert all(0 <= value <= 4095 for value in values)


def test_raw_values_to_voltages() -> None:
    assert raw_values_to_voltages([0, 4095], reference_voltage=3.3) == [0.0, 3.3]


def test_summarize_batch_computes_basic_statistics() -> None:
    summary = summarize_batch([0, 2048, 4095], reference_voltage=3.3)

    assert summary.min_voltage == 0.0
    assert summary.max_voltage == 3.3
    assert summary.average_voltage == pytest.approx(1.6504, abs=0.001)
    assert summary.rms_voltage > 0.0
    assert len(summary.downsampled_voltages) == 3


def test_summarize_batch_downsamples_large_batch() -> None:
    # The processor limits plot points so the GUI stays responsive.
    summary = summarize_batch(list(range(100)), max_downsampled_points=10)

    assert len(summary.downsampled_voltages) == 10


def test_batch_time_axis_seconds() -> None:
    assert batch_time_axis_seconds(sample_count=3, sample_rate_hz=10) == [0.0, 0.1, 0.2]


def test_high_rate_plot_history_stores_rolling_batches() -> None:
    history = HighRatePlotHistory(window_seconds=10.0)

    history.update_processed_batch(
        sensor_id="sensor-a",
        channel=0,
        start_timestamp_us=1_000_000,
        sample_rate_hz=10,
        sample_count=3,
        voltages=[1.0, 2.0, 3.0],
    )
    history.update_processed_batch(
        sensor_id="sensor-a",
        channel=0,
        start_timestamp_us=1_300_000,
        sample_rate_hz=10,
        sample_count=2,
        voltages=[4.0, 5.0],
    )

    assert history.channel_keys() == [("sensor-a", 0)]
    x_values, y_values = history.voltage_series("sensor-a", 0)
    assert x_values == pytest.approx([0.0, 0.1, 0.2, 0.3, 0.4])
    assert y_values == [1.0, 2.0, 3.0, 4.0, 5.0]


def test_high_rate_plot_history_prunes_old_points() -> None:
    history = HighRatePlotHistory(window_seconds=0.25)

    history.update_processed_batch(
        sensor_id="sensor-a",
        channel=0,
        start_timestamp_us=1_000_000,
        sample_rate_hz=10,
        sample_count=2,
        voltages=[1.0, 2.0],
    )
    history.update_processed_batch(
        sensor_id="sensor-a",
        channel=0,
        start_timestamp_us=1_200_000,
        sample_rate_hz=10,
        sample_count=2,
        voltages=[3.0, 4.0],
    )
    history.update_processed_batch(
        sensor_id="sensor-a",
        channel=0,
        start_timestamp_us=1_400_000,
        sample_rate_hz=10,
        sample_count=2,
        voltages=[5.0, 6.0],
    )

    x_values, y_values = history.voltage_series("sensor-a", 0)
    assert x_values == pytest.approx([0.0, 0.1, 0.2])
    assert y_values == [4.0, 5.0, 6.0]


def test_high_rate_plot_history_smooths_large_timestamp_gap() -> None:
    # Large wall-clock gaps are smoothed so the simulator plots as a continuous stream.
    history = HighRatePlotHistory(window_seconds=10.0)

    history.update_processed_batch(
        sensor_id="sensor-a",
        channel=0,
        start_timestamp_us=1_000_000,
        sample_rate_hz=10,
        sample_count=2,
        voltages=[1.0, 2.0],
    )
    history.update_processed_batch(
        sensor_id="sensor-a",
        channel=0,
        start_timestamp_us=5_000_000,
        sample_rate_hz=10,
        sample_count=2,
        voltages=[3.0, 4.0],
    )

    x_values, y_values = history.voltage_series("sensor-a", 0)
    assert x_values == pytest.approx([0.0, 0.1, 0.2, 0.3])
    assert y_values == [1.0, 2.0, 3.0, 4.0]


def test_high_rate_plot_history_rejects_invalid_window() -> None:
    with pytest.raises(ValueError):
        HighRatePlotHistory(window_seconds=0.0)
