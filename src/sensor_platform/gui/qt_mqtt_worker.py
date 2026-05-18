"""MQTT worker object used by the PySide6 GUI monitor."""

from __future__ import annotations

import paho.mqtt.client as mqtt
from PySide6.QtCore import QObject, Signal, Slot

from sensor_platform.core.mqtt_client import create_client
from sensor_platform.gui.config import GUI_STREAMS, GuiStreamConfig


class MqttWorker(QObject):
    """Runs MQTT callbacks away from the Qt UI thread."""

    # Qt signals safely move decoded messages from the MQTT thread to the GUI thread.
    connected = Signal()
    disconnected = Signal()
    error = Signal(str)
    decoded_message = Signal(str, object)

    def __init__(
        self,
        *,
        mqtt_host: str,
        mqtt_port: int,
        streams: list[GuiStreamConfig] | None = None,
    ) -> None:
        super().__init__()
        self._mqtt_host = mqtt_host
        self._mqtt_port = mqtt_port
        self._streams = GUI_STREAMS if streams is None else streams
        self._streams_by_topic = {stream.topic: stream for stream in self._streams}
        self._client: mqtt.Client | None = None

    @Slot()
    def start(self) -> None:
        """Connect to MQTT and block in the worker thread's network loop."""
        client = create_client("qt-monitor")
        client.on_connect = self._on_connect
        client.on_disconnect = self._on_disconnect
        client.on_message = self._on_message
        self._client = client

        try:
            client.connect(self._mqtt_host, self._mqtt_port)
            client.loop_forever()
        except Exception as exc:  # noqa: BLE001 - errors are surfaced in the GUI.
            self.error.emit(str(exc))
            self.disconnected.emit()

    @Slot()
    def stop(self) -> None:
        """Disconnecting causes loop_forever() to return and the worker thread to stop."""
        if self._client is not None:
            self._client.disconnect()

    def _on_connect(
        self,
        client: mqtt.Client,
        userdata: object,
        flags: mqtt.ConnectFlags,
        reason_code: mqtt.ReasonCode,
        properties: mqtt.Properties | None,
    ) -> None:
        # Stream config controls which topics the GUI watches.
        if reason_code.is_failure:
            self.error.emit(f"Failed to connect to MQTT broker: {reason_code}")
            return
        client.subscribe([(stream.topic, 0) for stream in self._streams])
        self.connected.emit()

    def _on_disconnect(
        self,
        client: mqtt.Client,
        userdata: object,
        flags: mqtt.DisconnectFlags,
        reason_code: mqtt.ReasonCode,
        properties: mqtt.Properties | None,
    ) -> None:
        self.disconnected.emit()

    def _on_message(self, client: mqtt.Client, userdata: object, message: mqtt.MQTTMessage) -> None:
        try:
            # Decode by topic because each topic carries a different protobuf message type.
            stream = self._streams_by_topic.get(message.topic)
            if stream is None:
                self.error.emit(f"Skipping unconfigured topic: {message.topic}")
                return
            self.decoded_message.emit(stream.name, stream.parser(message.payload))
        except ValueError as exc:
            self.error.emit(f"Skipping invalid payload on {message.topic}: {exc}")
