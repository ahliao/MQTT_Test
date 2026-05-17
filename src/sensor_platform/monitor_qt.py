from __future__ import annotations

import argparse
import sys

import pyqtgraph as pg
from PySide6.QtCore import QThread, QTimer, Slot
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from sensor_platform.config import MQTT_HOST, MQTT_PORT
from sensor_platform.generated import sensor_platform_pb2
from sensor_platform.monitor_state import ChannelSnapshot, MonitorState
from sensor_platform.plot_history import PlotHistory
from sensor_platform.qt_mqtt_worker import MqttWorker


TABLE_HEADERS = ["Sensor", "Ch", "Raw", "Voltage", "Avg Voltage", "State", "Timestamp ms"]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Display MQTT sensor data in a PySide6 GUI.")
    parser.add_argument("--mqtt-host", default=MQTT_HOST)
    parser.add_argument("--mqtt-port", type=int, default=MQTT_PORT)
    parser.add_argument("--max-points", type=int, default=300)
    return parser


class MonitorWindow(QMainWindow):
    def __init__(self, *, mqtt_host: str, mqtt_port: int, max_points: int) -> None:
        super().__init__()
        self.setWindowTitle("Sensor Platform Monitor")
        self.resize(1000, 700)

        self._state = MonitorState()
        self._history = PlotHistory(max_points=max_points)
        self._selected_channel: tuple[str, int] | None = None
        self._plot_paused = False

        self._status_label = QLabel(f"Connecting to MQTT at {mqtt_host}:{mqtt_port}...")
        self._channel_selector = QComboBox()
        self._channel_selector.currentIndexChanged.connect(self._select_channel_from_combo)

        self._pause_button = QPushButton("Pause Plot")
        self._pause_button.clicked.connect(self._toggle_plot_pause)
        self._clear_button = QPushButton("Clear Plot")
        self._clear_button.clicked.connect(self._clear_plot)

        self._table = QTableWidget(0, len(TABLE_HEADERS))
        self._table.setHorizontalHeaderLabels(TABLE_HEADERS)

        self._plot = pg.PlotWidget(title="Voltage Over Time")
        self._plot.setLabel("left", "Voltage", units="V")
        self._plot.setLabel("bottom", "Time", units="s")
        self._plot.addLegend()
        self._raw_curve = self._plot.plot(pen=pg.mkPen("#2d7ff9", width=2), name="Raw voltage")
        self._average_curve = self._plot.plot(
            pen=pg.mkPen("#f59f00", width=2),
            name="Moving average",
        )

        controls = QHBoxLayout()
        controls.addWidget(QLabel("Plot channel:"))
        controls.addWidget(self._channel_selector)
        controls.addWidget(self._pause_button)
        controls.addWidget(self._clear_button)
        controls.addStretch()

        layout = QVBoxLayout()
        layout.addWidget(self._status_label)
        layout.addWidget(self._table)
        layout.addLayout(controls)
        layout.addWidget(self._plot)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

        self._thread = QThread(self)
        self._worker = MqttWorker(mqtt_host=mqtt_host, mqtt_port=mqtt_port)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.start)
        self._worker.connected.connect(self._handle_connected)
        self._worker.disconnected.connect(self._handle_disconnected)
        self._worker.error.connect(self._handle_error)
        self._worker.raw_reading.connect(self._handle_raw_reading)
        self._worker.processed_reading.connect(self._handle_processed_reading)

        self._timer = QTimer(self)
        self._timer.setInterval(250)
        self._timer.timeout.connect(self._refresh_plot)
        self._timer.start()

        self._thread.start()

    @Slot()
    def _handle_connected(self) -> None:
        self._status_label.setText("Connected to MQTT broker")

    @Slot()
    def _handle_disconnected(self) -> None:
        self._status_label.setText("Disconnected from MQTT broker")

    @Slot(str)
    def _handle_error(self, message: str) -> None:
        self._status_label.setText(message)

    @Slot(object)
    def _handle_raw_reading(self, reading: sensor_platform_pb2.AdcReading) -> None:
        self._state.update_raw(reading)
        self._history.add_raw(
            sensor_id=reading.sensor_id,
            channel=reading.channel,
            timestamp_ms=reading.timestamp_ms,
            voltage=reading.voltage,
        )
        self._refresh_table()
        self._refresh_channel_selector()

    @Slot(object)
    def _handle_processed_reading(self, reading: sensor_platform_pb2.ProcessedReading) -> None:
        self._state.update_processed(reading)
        self._history.add_processed(
            sensor_id=reading.sensor_id,
            channel=reading.channel,
            timestamp_ms=reading.timestamp_ms,
            moving_average_voltage=reading.moving_average_voltage,
        )
        self._refresh_table()
        self._refresh_channel_selector()

    def _refresh_table(self) -> None:
        snapshots = self._state.snapshots()
        self._table.setRowCount(len(snapshots))
        for row, snapshot in enumerate(snapshots):
            values = self._format_snapshot(snapshot)
            for column, value in enumerate(values):
                self._table.setItem(row, column, QTableWidgetItem(value))
        self._table.resizeColumnsToContents()

    def _refresh_channel_selector(self) -> None:
        keys = self._history.channel_keys()
        current = self._selected_channel
        if current is None and keys:
            current = keys[0]
            self._selected_channel = current

        labels = [self._channel_label(sensor_id, channel) for sensor_id, channel in keys]
        existing_labels = [self._channel_selector.itemText(index) for index in range(self._channel_selector.count())]
        if labels == existing_labels:
            return

        self._channel_selector.blockSignals(True)
        self._channel_selector.clear()
        for sensor_id, channel in keys:
            self._channel_selector.addItem(self._channel_label(sensor_id, channel), (sensor_id, channel))
        if current in keys:
            self._channel_selector.setCurrentIndex(keys.index(current))
        self._channel_selector.blockSignals(False)

    def _refresh_plot(self) -> None:
        if self._plot_paused or self._selected_channel is None:
            return

        sensor_id, channel = self._selected_channel
        raw_x, raw_y = self._history.raw_series(sensor_id, channel)
        average_x, average_y = self._history.moving_average_series(sensor_id, channel)
        self._raw_curve.setData(raw_x, raw_y)
        self._average_curve.setData(average_x, average_y)

    def _select_channel_from_combo(self) -> None:
        data = self._channel_selector.currentData()
        if data is not None:
            self._selected_channel = data
            self._refresh_plot()

    def _toggle_plot_pause(self) -> None:
        self._plot_paused = not self._plot_paused
        self._pause_button.setText("Resume Plot" if self._plot_paused else "Pause Plot")

    def _clear_plot(self) -> None:
        self._history.clear()
        self._selected_channel = None
        self._channel_selector.clear()
        self._raw_curve.setData([], [])
        self._average_curve.setData([], [])

    def closeEvent(self, event: object) -> None:
        self._worker.stop()
        self._thread.quit()
        self._thread.wait(3000)
        super().closeEvent(event)

    @staticmethod
    def _format_snapshot(snapshot: ChannelSnapshot) -> list[str]:
        raw = "-" if snapshot.raw_value is None else str(snapshot.raw_value)
        voltage = "-" if snapshot.voltage is None else f"{snapshot.voltage:.3f} V"
        average = (
            "-"
            if snapshot.moving_average_voltage is None
            else f"{snapshot.moving_average_voltage:.3f} V"
        )
        return [
            snapshot.sensor_id,
            str(snapshot.channel),
            raw,
            voltage,
            average,
            snapshot.state or "-",
            str(snapshot.timestamp_ms),
        ]

    @staticmethod
    def _channel_label(sensor_id: str, channel: int) -> str:
        return f"{sensor_id} / channel {channel}"


def main() -> None:
    args = build_parser().parse_args()
    app = QApplication(sys.argv)
    window = MonitorWindow(
        mqtt_host=args.mqtt_host,
        mqtt_port=args.mqtt_port,
        max_points=args.max_points,
    )
    window.show()
    raise SystemExit(app.exec())


if __name__ == "__main__":
    main()
