from __future__ import annotations

import paho.mqtt.client as mqtt
from PySide6.QtCore import QObject, Signal, Slot

from sensor_platform.config import PROCESSOR_RESULTS_TOPIC, SENSOR_READINGS_TOPIC
from sensor_platform.generated import sensor_platform_pb2
from sensor_platform.mqtt_client import create_client
from sensor_platform.protobuf_helpers import parse_adc_reading, parse_processed_reading


class MqttWorker(QObject):
    """Runs MQTT callbacks away from the Qt UI thread."""

    connected = Signal()
    disconnected = Signal()
    error = Signal(str)
    raw_reading = Signal(object)
    processed_reading = Signal(object)

    def __init__(self, *, mqtt_host: str, mqtt_port: int) -> None:
        super().__init__()
        self._mqtt_host = mqtt_host
        self._mqtt_port = mqtt_port
        self._client: mqtt.Client | None = None

    @Slot()
    def start(self) -> None:
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
        if reason_code.is_failure:
            self.error.emit(f"Failed to connect to MQTT broker: {reason_code}")
            return
        client.subscribe([(SENSOR_READINGS_TOPIC, 0), (PROCESSOR_RESULTS_TOPIC, 0)])
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
            if message.topic == SENSOR_READINGS_TOPIC:
                reading: sensor_platform_pb2.AdcReading = parse_adc_reading(message.payload)
                self.raw_reading.emit(reading)
            elif message.topic == PROCESSOR_RESULTS_TOPIC:
                processed: sensor_platform_pb2.ProcessedReading = parse_processed_reading(message.payload)
                self.processed_reading.emit(processed)
        except ValueError as exc:
            self.error.emit(f"Skipping invalid payload on {message.topic}: {exc}")
