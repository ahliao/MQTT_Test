"""GUI view of the shared MQTT/protobuf stream registry."""

from __future__ import annotations

from sensor_platform.streams import (
    HIGH_RATE_PROCESSED_ADC_STREAM,
    PROCESSED_ADC_STREAM,
    RAW_ADC_STREAM,
    StreamConfig,
    default_visible_streams,
)


GuiStreamConfig = StreamConfig

# The GUI subscribes to streams with display handlers today. Raw high-rate
# batches stay registered globally but hidden until the GUI has a raw-batch view.
GUI_STREAMS = default_visible_streams()

__all__ = [
    "GUI_STREAMS",
    "GuiStreamConfig",
    "HIGH_RATE_PROCESSED_ADC_STREAM",
    "PROCESSED_ADC_STREAM",
    "RAW_ADC_STREAM",
]
