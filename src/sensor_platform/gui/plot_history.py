"""In-memory history buffers used by the CLI/GUI monitor displays."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass


@dataclass(frozen=True)
class PlotPoint:
    """One low-rate plot point; raw and processed values may arrive separately."""

    timestamp_ms: int
    raw_voltage: float | None = None
    moving_average_voltage: float | None = None


@dataclass(frozen=True)
class HighRatePlotPoint:
    """One downsampled point from a processed high-rate batch."""

    timestamp_s: float
    voltage: float


class PlotHistory:
    """Keeps recent voltage samples for live plotting."""

    def __init__(self, *, max_points: int = 300) -> None:
        if max_points < 1:
            raise ValueError("max_points must be at least 1")
        self._points_by_channel: dict[tuple[str, int], deque[PlotPoint]] = {}
        self._max_points = max_points

    def add_raw(
        self,
        *,
        sensor_id: str,
        channel: int,
        timestamp_ms: int,
        voltage: float,
    ) -> None:
        """Add a raw low-rate voltage point for one sensor/channel."""
        self._points(sensor_id, channel).append(
            PlotPoint(timestamp_ms=timestamp_ms, raw_voltage=voltage)
        )

    def add_processed(
        self,
        *,
        sensor_id: str,
        channel: int,
        timestamp_ms: int,
        moving_average_voltage: float,
    ) -> None:
        """Add a processed low-rate moving-average point for one sensor/channel."""
        self._points(sensor_id, channel).append(
            PlotPoint(
                timestamp_ms=timestamp_ms,
                moving_average_voltage=moving_average_voltage,
            )
        )

    def channel_keys(self) -> list[tuple[str, int]]:
        return sorted(self._points_by_channel)

    def raw_series(self, sensor_id: str, channel: int) -> tuple[list[float], list[float]]:
        return self._series(sensor_id, channel, "raw_voltage")

    def moving_average_series(self, sensor_id: str, channel: int) -> tuple[list[float], list[float]]:
        return self._series(sensor_id, channel, "moving_average_voltage")

    def clear(self) -> None:
        self._points_by_channel.clear()

    def _points(self, sensor_id: str, channel: int) -> deque[PlotPoint]:
        key = (sensor_id, channel)
        if key not in self._points_by_channel:
            self._points_by_channel[key] = deque(maxlen=self._max_points)
        return self._points_by_channel[key]

    def _series(
        self,
        sensor_id: str,
        channel: int,
        field_name: str,
    ) -> tuple[list[float], list[float]]:
        """Return x/y lists relative to the first retained point."""
        points = self._points_by_channel.get((sensor_id, channel), ())
        values = [point for point in points if getattr(point, field_name) is not None]
        if not values:
            return [], []

        first_timestamp_ms = values[0].timestamp_ms
        x_values = [(point.timestamp_ms - first_timestamp_ms) / 1000.0 for point in values]
        y_values = [float(getattr(point, field_name)) for point in values]
        return x_values, y_values


class HighRatePlotHistory:
    """Stores a rolling time window of processed high-rate batch samples."""

    def __init__(self, *, window_seconds: float = 10.0) -> None:
        if window_seconds <= 0:
            raise ValueError("window_seconds must be greater than 0")
        self._points_by_channel: dict[tuple[str, int], deque[HighRatePlotPoint]] = {}
        self._last_sample_timestamp_by_channel: dict[tuple[str, int], float] = {}
        self._window_seconds = window_seconds

    def update_processed_batch(
        self,
        *,
        sensor_id: str,
        channel: int,
        start_timestamp_us: int,
        sample_rate_hz: int,
        sample_count: int,
        voltages: list[float],
    ) -> None:
        """Append one processed high-rate batch to the rolling plot window."""
        if sample_rate_hz < 1:
            raise ValueError("sample_rate_hz must be at least 1")
        if sample_count < 1:
            raise ValueError("sample_count must be at least 1")
        if not voltages:
            return

        key = (sensor_id, channel)
        points = self._points(sensor_id, channel)
        start_timestamp_s = self._continuous_start_timestamp_s(
            key=key,
            start_timestamp_us=start_timestamp_us,
            sample_rate_hz=sample_rate_hz,
            sample_count=sample_count,
        )
        # Downsampled voltages map back onto their approximate original sample positions.
        for index, voltage in enumerate(voltages):
            sample_offset = self._sample_offset(index, len(voltages), sample_count)
            timestamp_s = start_timestamp_s + (sample_offset / sample_rate_hz)
            points.append(HighRatePlotPoint(timestamp_s=timestamp_s, voltage=voltage))

        self._last_sample_timestamp_by_channel[key] = start_timestamp_s + (
            (sample_count - 1) / sample_rate_hz
        )
        newest_timestamp_s = points[-1].timestamp_s
        cutoff_s = newest_timestamp_s - self._window_seconds
        # Keep memory bounded by discarding points outside the visible rolling window.
        while points and points[0].timestamp_s < cutoff_s:
            points.popleft()

    def channel_keys(self) -> list[tuple[str, int]]:
        return sorted(self._points_by_channel)

    def voltage_series(self, sensor_id: str, channel: int) -> tuple[list[float], list[float]]:
        """Return high-rate x/y lists relative to the oldest retained point."""
        points = self._points_by_channel.get((sensor_id, channel))
        if not points:
            return [], []
        first_timestamp_s = points[0].timestamp_s
        x_values = [point.timestamp_s - first_timestamp_s for point in points]
        y_values = [point.voltage for point in points]
        return x_values, y_values

    def clear(self) -> None:
        self._points_by_channel.clear()
        self._last_sample_timestamp_by_channel.clear()

    def _points(self, sensor_id: str, channel: int) -> deque[HighRatePlotPoint]:
        key = (sensor_id, channel)
        if key not in self._points_by_channel:
            self._points_by_channel[key] = deque()
        return self._points_by_channel[key]

    @staticmethod
    def _sample_offset(index: int, voltage_count: int, sample_count: int) -> float:
        if voltage_count == 1:
            return 0.0
        return index * ((sample_count - 1) / (voltage_count - 1))

    def _continuous_start_timestamp_s(
        self,
        *,
        key: tuple[str, int],
        start_timestamp_us: int,
        sample_rate_hz: int,
        sample_count: int,
    ) -> float:
        """Smooth unrealistic wall-clock gaps in the educational simulator stream."""
        measured_start_s = start_timestamp_us / 1_000_000.0
        last_sample_timestamp_s = self._last_sample_timestamp_by_channel.get(key)
        if last_sample_timestamp_s is None:
            return measured_start_s

        expected_start_s = last_sample_timestamp_s + (1.0 / sample_rate_hz)
        batch_duration_s = sample_count / sample_rate_hz
        allowed_gap_s = max(0.25, batch_duration_s * 4)
        # Large gaps are usually OS scheduling artifacts, not missing simulated samples.
        if abs(measured_start_s - expected_start_s) > allowed_gap_s:
            return expected_start_s
        return measured_start_s
