"""Shared monitor state for combining raw and processed low-rate messages."""

from __future__ import annotations

from dataclasses import dataclass

from sensor_platform.generated import sensor_platform_pb2


@dataclass
class ChannelSnapshot:
    """Latest known values for one sensor/channel pair."""

    sensor_id: str
    channel: int
    timestamp_ms: int
    raw_value: int | None = None
    voltage: float | None = None
    moving_average_voltage: float | None = None
    state: str | None = None


class MonitorState:
    """Stores latest readings separately from how they are displayed."""

    def __init__(self) -> None:
        self._snapshots: dict[tuple[str, int], ChannelSnapshot] = {}

    def update_raw(self, reading: sensor_platform_pb2.AdcReading) -> None:
        """Merge a raw reading into the existing snapshot for this channel."""
        key = (reading.sensor_id, reading.channel)
        snapshot = self._snapshots.get(
            key,
            ChannelSnapshot(
                sensor_id=reading.sensor_id,
                channel=reading.channel,
                timestamp_ms=reading.timestamp_ms,
            ),
        )
        snapshot.timestamp_ms = reading.timestamp_ms
        snapshot.raw_value = reading.raw_value
        snapshot.voltage = reading.voltage
        self._snapshots[key] = snapshot

    def update_processed(self, reading: sensor_platform_pb2.ProcessedReading) -> None:
        """Merge processed values without discarding the latest raw count."""
        key = (reading.sensor_id, reading.channel)
        snapshot = self._snapshots.get(
            key,
            ChannelSnapshot(
                sensor_id=reading.sensor_id,
                channel=reading.channel,
                timestamp_ms=reading.timestamp_ms,
            ),
        )
        snapshot.timestamp_ms = reading.timestamp_ms
        snapshot.voltage = reading.voltage
        snapshot.moving_average_voltage = reading.moving_average_voltage
        snapshot.state = reading.state
        self._snapshots[key] = snapshot

    def snapshots(self) -> list[ChannelSnapshot]:
        """Return snapshots in stable order so displays do not jump around."""
        return sorted(self._snapshots.values(), key=lambda item: (item.sensor_id, item.channel))
