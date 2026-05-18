"""PySide6 GUI monitor for low-rate and high-rate MQTT/protobuf streams."""

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
from sensor_platform.gui.config import (
    HIGH_RATE_PROCESSED_ADC_STREAM,
    PROCESSED_ADC_STREAM,
    RAW_ADC_STREAM,
)
from sensor_platform.gui.plot_history import HighRatePlotHistory, PlotHistory
from sensor_platform.gui.qt_mqtt_worker import MqttWorker
from sensor_platform.monitors.monitor_state import ChannelSnapshot, MonitorState


TABLE_HEADERS = ["Sensor", "Ch", "Raw", "Voltage", "Avg Voltage", "State", "Timestamp ms"]
HIGH_RATE_TABLE_HEADERS = [
    "Sensor",
    "Ch",
    "Samples",
    "Rate",
    "Min",
    "Max",
    "Avg",
    "RMS",
    "Start us",
]


def build_parser() -> argparse.ArgumentParser:
    """Define GUI, broker, and plot-history options."""
    parser = argparse.ArgumentParser(description="Display MQTT sensor data in a PySide6 GUI.")
    parser.add_argument("--mqtt-host", default=MQTT_HOST)
    parser.add_argument("--mqtt-port", type=int, default=MQTT_PORT)
    parser.add_argument("--max-points", type=int, default=300)
    parser.add_argument("--high-rate-window-seconds", type=float, default=10.0)
    return parser


class MonitorWindow(QMainWindow):
    """Main GUI window that owns tables, plots, and the MQTT worker thread."""

    def __init__(
        self,
        *,
        mqtt_host: str,
        mqtt_port: int,
        max_points: int,
        high_rate_window_seconds: float,
    ) -> None:
        super().__init__()
        self.setWindowTitle("Sensor Platform Monitor")
        self.resize(1000, 700)

        # State objects keep data handling separate from Qt widgets.
        self._state = MonitorState()
        self._history = PlotHistory(max_points=max_points)
        self._high_rate_history = HighRatePlotHistory(window_seconds=high_rate_window_seconds)
        self._high_rate_summaries: dict[
            tuple[str, int], sensor_platform_pb2.ProcessedSampleBatch
        ] = {}
        self._selected_channel: tuple[str, int] | None = None
        self._selected_high_rate_channel: tuple[str, int] | None = None
        self._plot_paused = False

        # Top-level status and controls.
        self._status_label = QLabel(f"Connecting to MQTT at {mqtt_host}:{mqtt_port}...")
        self._channel_selector = QComboBox()
        self._channel_selector.currentIndexChanged.connect(self._select_channel_from_combo)
        self._high_rate_channel_selector = QComboBox()
        self._high_rate_channel_selector.currentIndexChanged.connect(
            self._select_high_rate_channel_from_combo
        )

        self._pause_button = QPushButton("Pause Plot")
        self._pause_button.clicked.connect(self._toggle_plot_pause)
        self._clear_button = QPushButton("Clear Plot")
        self._clear_button.clicked.connect(self._clear_plot)

        self._table = QTableWidget(0, len(TABLE_HEADERS))
        self._table.setHorizontalHeaderLabels(TABLE_HEADERS)
        self._high_rate_table = QTableWidget(0, len(HIGH_RATE_TABLE_HEADERS))
        self._high_rate_table.setHorizontalHeaderLabels(HIGH_RATE_TABLE_HEADERS)

        # Low-rate plot shows raw voltage and moving average over time.
        self._plot = pg.PlotWidget(title="Voltage Over Time")
        self._plot.setLabel("left", "Voltage", units="V")
        self._plot.setLabel("bottom", "Time", units="s")
        self._plot.addLegend()
        self._raw_curve = self._plot.plot(pen=pg.mkPen("#2d7ff9", width=2), name="Raw voltage")
        self._average_curve = self._plot.plot(
            pen=pg.mkPen("#f59f00", width=2),
            name="Moving average",
        )

        # High-rate plot shows downsampled points from processed sample batches.
        self._high_rate_plot = pg.PlotWidget(title="High-Rate Rolling Capture")
        self._high_rate_plot.setLabel("left", "Voltage", units="V")
        self._high_rate_plot.setLabel("bottom", "Time in rolling window", units="s")
        self._high_rate_plot.addLegend()
        self._high_rate_curve = self._high_rate_plot.plot(
            pen=pg.mkPen("#12b886", width=2),
            name="Downsampled batch voltage",
        )

        controls = QHBoxLayout()
        controls.addWidget(QLabel("Plot channel:"))
        controls.addWidget(self._channel_selector)
        controls.addWidget(self._pause_button)
        controls.addWidget(self._clear_button)
        controls.addStretch()

        high_rate_controls = QHBoxLayout()
        high_rate_controls.addWidget(QLabel("High-rate channel:"))
        high_rate_controls.addWidget(self._high_rate_channel_selector)
        high_rate_controls.addStretch()

        # The layout stacks status, tables, controls, and plots vertically.
        layout = QVBoxLayout()
        layout.addWidget(self._status_label)
        layout.addWidget(QLabel("Low-rate sensor stream"))
        layout.addWidget(self._table)
        layout.addWidget(QLabel("High-rate batch stream"))
        layout.addWidget(self._high_rate_table)
        layout.addLayout(controls)
        layout.addWidget(self._plot)
        layout.addLayout(high_rate_controls)
        layout.addWidget(self._high_rate_plot)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

        # MQTT runs in a QThread so network callbacks never block the GUI event loop.
        self._thread = QThread(self)
        self._worker = MqttWorker(mqtt_host=mqtt_host, mqtt_port=mqtt_port)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.start)
        self._worker.connected.connect(self._handle_connected)
        self._worker.disconnected.connect(self._handle_disconnected)
        self._worker.error.connect(self._handle_error)
        self._worker.decoded_message.connect(self._handle_decoded_message)

        # A timer redraws plots at a steady GUI-friendly rate.
        self._timer = QTimer(self)
        self._timer.setInterval(250)
        self._timer.timeout.connect(self._refresh_plot)
        self._timer.start()

        self._thread.start()

    @Slot()
    def _handle_connected(self) -> None:
        """Show broker connection status in the GUI."""
        self._status_label.setText("Connected to MQTT broker")

    @Slot()
    def _handle_disconnected(self) -> None:
        """Show broker disconnect status in the GUI."""
        self._status_label.setText("Disconnected from MQTT broker")

    @Slot(str)
    def _handle_error(self, message: str) -> None:
        """Surface worker errors without crashing the GUI thread."""
        self._status_label.setText(message)

    @Slot(str, object)
    def _handle_decoded_message(self, stream_name: str, message: object) -> None:
        """Route decoded messages from configured streams to the right display handler."""
        if stream_name == RAW_ADC_STREAM:
            self._handle_raw_reading(message)
        elif stream_name == PROCESSED_ADC_STREAM:
            self._handle_processed_reading(message)
        elif stream_name == HIGH_RATE_PROCESSED_ADC_STREAM:
            self._handle_high_rate_processed_batch(message)
        else:
            self._status_label.setText(f"No GUI handler configured for stream: {stream_name}")

    def _handle_raw_reading(self, reading: sensor_platform_pb2.AdcReading) -> None:
        """Receive low-rate raw readings from the MQTT worker."""
        self._state.update_raw(reading)
        self._history.add_raw(
            sensor_id=reading.sensor_id,
            channel=reading.channel,
            timestamp_ms=reading.timestamp_ms,
            voltage=reading.voltage,
        )
        self._refresh_table()
        self._refresh_channel_selector()

    def _handle_processed_reading(self, reading: sensor_platform_pb2.ProcessedReading) -> None:
        """Receive low-rate processed readings from the MQTT worker."""
        self._state.update_processed(reading)
        self._history.add_processed(
            sensor_id=reading.sensor_id,
            channel=reading.channel,
            timestamp_ms=reading.timestamp_ms,
            moving_average_voltage=reading.moving_average_voltage,
        )
        self._refresh_table()
        self._refresh_channel_selector()

    def _handle_high_rate_processed_batch(
        self,
        batch: sensor_platform_pb2.ProcessedSampleBatch,
    ) -> None:
        """Receive high-rate summaries and append them to the rolling plot."""
        self._high_rate_summaries[(batch.sensor_id, batch.channel)] = batch
        self._high_rate_history.update_processed_batch(
            sensor_id=batch.sensor_id,
            channel=batch.channel,
            start_timestamp_us=batch.start_timestamp_us,
            sample_rate_hz=batch.sample_rate_hz,
            sample_count=batch.sample_count,
            voltages=list(batch.downsampled_voltages),
        )
        self._status_label.setText(
            f"Connected. Latest high-rate batch: {batch.sample_count} samples, "
            f"avg={batch.average_voltage:.3f} V, rms={batch.rms_voltage:.3f} V"
        )
        self._refresh_high_rate_table()
        self._refresh_high_rate_channel_selector()
        self._refresh_plot()

    def _refresh_table(self) -> None:
        """Redraw the low-rate table from the latest channel snapshots."""
        snapshots = self._state.snapshots()
        self._table.setRowCount(len(snapshots))
        for row, snapshot in enumerate(snapshots):
            values = self._format_snapshot(snapshot)
            for column, value in enumerate(values):
                self._table.setItem(row, column, QTableWidgetItem(value))
        self._table.resizeColumnsToContents()

    def _refresh_high_rate_table(self) -> None:
        """Redraw the high-rate summary table from the latest processed batches."""
        summaries = [
            self._high_rate_summaries[key]
            for key in sorted(self._high_rate_summaries, key=lambda item: (item[0], item[1]))
        ]
        self._high_rate_table.setRowCount(len(summaries))
        for row, summary in enumerate(summaries):
            values = self._format_high_rate_summary(summary)
            for column, value in enumerate(values):
                self._high_rate_table.setItem(row, column, QTableWidgetItem(value))
        self._high_rate_table.resizeColumnsToContents()

    def _refresh_channel_selector(self) -> None:
        """Keep the low-rate channel selector in sync with received data."""
        keys = self._history.channel_keys()
        current = self._selected_channel
        if current is None and keys:
            current = keys[0]
            self._selected_channel = current

        labels = [self._channel_label(sensor_id, channel) for sensor_id, channel in keys]
        existing_labels = [
            self._channel_selector.itemText(index) for index in range(self._channel_selector.count())
        ]
        if labels == existing_labels:
            return

        self._channel_selector.blockSignals(True)
        self._channel_selector.clear()
        for sensor_id, channel in keys:
            self._channel_selector.addItem(self._channel_label(sensor_id, channel), (sensor_id, channel))
        if current in keys:
            self._channel_selector.setCurrentIndex(keys.index(current))
        self._channel_selector.blockSignals(False)

    def _refresh_high_rate_channel_selector(self) -> None:
        """Keep the high-rate channel selector in sync with received data."""
        keys = self._high_rate_history.channel_keys()
        current = self._selected_high_rate_channel
        if current is None and keys:
            current = keys[0]
            self._selected_high_rate_channel = current

        labels = [self._channel_label(sensor_id, channel) for sensor_id, channel in keys]
        existing_labels = [
            self._high_rate_channel_selector.itemText(index)
            for index in range(self._high_rate_channel_selector.count())
        ]
        if labels == existing_labels:
            return

        self._high_rate_channel_selector.blockSignals(True)
        self._high_rate_channel_selector.clear()
        for sensor_id, channel in keys:
            self._high_rate_channel_selector.addItem(
                self._channel_label(sensor_id, channel),
                (sensor_id, channel),
            )
        if current in keys:
            self._high_rate_channel_selector.setCurrentIndex(keys.index(current))
        self._high_rate_channel_selector.blockSignals(False)

    def _refresh_plot(self) -> None:
        """Update plot curves unless the user has paused plotting."""
        if self._plot_paused:
            return

        if self._selected_channel is not None:
            sensor_id, channel = self._selected_channel
            raw_x, raw_y = self._history.raw_series(sensor_id, channel)
            average_x, average_y = self._history.moving_average_series(sensor_id, channel)
            self._raw_curve.setData(raw_x, raw_y)
            self._average_curve.setData(average_x, average_y)

        if self._selected_high_rate_channel is not None:
            sensor_id, channel = self._selected_high_rate_channel
            batch_x, batch_y = self._high_rate_history.voltage_series(sensor_id, channel)
            self._high_rate_curve.setData(batch_x, batch_y)

    def _select_channel_from_combo(self) -> None:
        """Switch the low-rate plot to the selected sensor/channel."""
        data = self._channel_selector.currentData()
        if data is not None:
            self._selected_channel = data
            self._refresh_plot()

    def _select_high_rate_channel_from_combo(self) -> None:
        """Switch the high-rate plot to the selected sensor/channel."""
        data = self._high_rate_channel_selector.currentData()
        if data is not None:
            self._selected_high_rate_channel = data
            self._refresh_plot()

    def _toggle_plot_pause(self) -> None:
        """Pause drawing while still allowing MQTT data to be received."""
        self._plot_paused = not self._plot_paused
        self._pause_button.setText("Resume Plot" if self._plot_paused else "Pause Plot")

    def _clear_plot(self) -> None:
        """Clear plot histories and high-rate summaries from the GUI."""
        self._history.clear()
        self._high_rate_history.clear()
        self._high_rate_summaries.clear()
        self._selected_channel = None
        self._selected_high_rate_channel = None
        self._channel_selector.clear()
        self._high_rate_channel_selector.clear()
        self._high_rate_table.setRowCount(0)
        self._raw_curve.setData([], [])
        self._average_curve.setData([], [])
        self._high_rate_curve.setData([], [])

    def closeEvent(self, event: object) -> None:
        """Stop the MQTT worker before the Qt window exits."""
        self._worker.stop()
        self._thread.quit()
        self._thread.wait(3000)
        super().closeEvent(event)

    @staticmethod
    def _format_snapshot(snapshot: ChannelSnapshot) -> list[str]:
        """Convert a low-rate snapshot into display strings for the table."""
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
    def _format_high_rate_summary(summary: sensor_platform_pb2.ProcessedSampleBatch) -> list[str]:
        """Convert a high-rate processed batch into display strings for the table."""
        return [
            summary.sensor_id,
            str(summary.channel),
            str(summary.sample_count),
            f"{summary.sample_rate_hz} Hz",
            f"{summary.min_voltage:.3f} V",
            f"{summary.max_voltage:.3f} V",
            f"{summary.average_voltage:.3f} V",
            f"{summary.rms_voltage:.3f} V",
            str(summary.start_timestamp_us),
        ]

    @staticmethod
    def _channel_label(sensor_id: str, channel: int) -> str:
        return f"{sensor_id} / channel {channel}"


def main() -> None:
    """Create the Qt application and run the GUI event loop."""
    args = build_parser().parse_args()
    app = QApplication(sys.argv)
    window = MonitorWindow(
        mqtt_host=args.mqtt_host,
        mqtt_port=args.mqtt_port,
        max_points=args.max_points,
        high_rate_window_seconds=args.high_rate_window_seconds,
    )
    window.show()
    raise SystemExit(app.exec())


if __name__ == "__main__":
    main()
