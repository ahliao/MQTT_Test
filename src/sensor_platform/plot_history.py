from __future__ import annotations

from collections import deque
from dataclasses import dataclass


@dataclass(frozen=True)
class PlotPoint:
    timestamp_ms: int
    raw_voltage: float | None = None
    moving_average_voltage: float | None = None


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
        points = self._points_by_channel.get((sensor_id, channel), ())
        values = [point for point in points if getattr(point, field_name) is not None]
        if not values:
            return [], []

        first_timestamp_ms = values[0].timestamp_ms
        x_values = [(point.timestamp_ms - first_timestamp_ms) / 1000.0 for point in values]
        y_values = [float(getattr(point, field_name)) for point in values]
        return x_values, y_values
