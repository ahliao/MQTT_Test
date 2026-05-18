"""Tests for monitor plot history buffers."""

from __future__ import annotations

import pytest

from sensor_platform.gui.plot_history import PlotHistory


def test_plot_history_stores_raw_voltage_series() -> None:
    history = PlotHistory(max_points=5)

    history.add_raw(sensor_id="sensor-a", channel=0, timestamp_ms=1000, voltage=1.0)
    history.add_raw(sensor_id="sensor-a", channel=0, timestamp_ms=1500, voltage=1.5)

    x_values, y_values = history.raw_series("sensor-a", 0)

    assert x_values == [0.0, 0.5]
    assert y_values == [1.0, 1.5]


def test_plot_history_stores_moving_average_series() -> None:
    history = PlotHistory(max_points=5)

    history.add_processed(
        sensor_id="sensor-a",
        channel=0,
        timestamp_ms=1000,
        moving_average_voltage=1.2,
    )

    assert history.moving_average_series("sensor-a", 0) == ([0.0], [1.2])


def test_plot_history_limits_points() -> None:
    # The low-rate plot buffer uses a fixed point count to bound memory use.
    history = PlotHistory(max_points=2)

    history.add_raw(sensor_id="sensor-a", channel=0, timestamp_ms=1000, voltage=1.0)
    history.add_raw(sensor_id="sensor-a", channel=0, timestamp_ms=2000, voltage=2.0)
    history.add_raw(sensor_id="sensor-a", channel=0, timestamp_ms=3000, voltage=3.0)

    x_values, y_values = history.raw_series("sensor-a", 0)

    assert x_values == [0.0, 1.0]
    assert y_values == [2.0, 3.0]


def test_plot_history_reports_channels() -> None:
    history = PlotHistory(max_points=5)

    history.add_raw(sensor_id="sensor-b", channel=1, timestamp_ms=1000, voltage=1.0)
    history.add_raw(sensor_id="sensor-a", channel=0, timestamp_ms=1000, voltage=1.0)

    assert history.channel_keys() == [("sensor-a", 0), ("sensor-b", 1)]


def test_plot_history_rejects_invalid_max_points() -> None:
    with pytest.raises(ValueError):
        PlotHistory(max_points=0)
