# Qt GUI Monitor

## Goal

The Qt GUI monitor is a visual version of the CLI monitor. It subscribes to the same MQTT topics, decodes the same protobuf messages, and displays the same latest sensor and processor values.

It also adds a live plot of voltage over time using `pyqtgraph`. If the high-rate sensor and high-rate processor are running, the GUI shows a separate high-rate batch plot.

## What It Shows

- MQTT connection status
- Latest raw ADC value
- Latest raw voltage
- Latest moving average voltage
- Latest processor state such as `LOW`, `NORMAL`, or `HIGH`
- High-rate batch summary table with sample count, sample rate, min, max, average, and RMS voltage
- Live plot of raw voltage and moving average voltage
- Separate high-rate rolling plot for downsampled 10 kHz-style sample batches

The low-rate table is populated by `sensor/adc/readings` and `processor/adc/results`.

The high-rate table is populated by `processor/adc/high-rate/results`. The GUI does not show every raw high-rate sample in the table because a 10 kHz stream would create too many rows too quickly. Instead, it shows one summary row per high-rate sensor/channel and plots the downsampled waveform.

## Run It

Start Mosquitto first, then run the sensor and processor.

Run the GUI monitor with:

```bash
uv run python -m sensor_platform.gui.monitor_qt --mqtt-host localhost
```

Or use the project script:

```bash
uv run sensor-platform-monitor-gui --mqtt-host localhost
```

The high-rate plot keeps a rolling capture window. The default is `10` seconds:

```bash
uv run sensor-platform-monitor-gui --high-rate-window-seconds 10
```

## GUI Controls

- Plot channel: chooses which sensor/channel pair to plot.
- High-rate channel: chooses which high-rate sensor/channel pair to plot.
- Pause Plot: freezes plot updates while MQTT messages continue updating the table.
- Resume Plot: resumes plot updates.
- Clear Plot: clears stored plot history.

## How It Is Structured

The GUI keeps MQTT work away from the Qt UI thread.

```text
MqttWorker in QThread
        |
        | decoded protobuf messages via Qt signals
        v
MonitorWindow
        |
        +--> MonitorState for latest table values
        +--> PlotHistory for pyqtgraph time series
        +--> HighRatePlotHistory for latest high-rate batch snapshots
```

Important files:

- `src/sensor_platform/gui/monitor_qt.py`: main PySide6 window
- `src/sensor_platform/gui/config.py`: configured MQTT topics and protobuf parsers
- `src/sensor_platform/gui/qt_mqtt_worker.py`: MQTT worker that subscribes from GUI config and emits decoded messages
- `src/sensor_platform/gui/plot_history.py`: rolling data history for plots
- `src/sensor_platform/sensors/high_rate_sensor.py`: high-rate batch publisher
- `src/sensor_platform/processors/high_rate_processor.py`: high-rate batch processor
- `src/sensor_platform/monitors/monitor_state.py`: latest values shared with the CLI monitor concept

## Config-Driven Streams

The GUI MQTT subscription layer is configured by `src/sensor_platform/gui/config.py`.

Each `GuiStreamConfig` defines:

- stream name
- display name
- MQTT topic
- protobuf parser
- stream kind

The MQTT worker uses this config to subscribe and parse messages. The main GUI window still owns the display-specific table and plot handlers.

## WSL Notes

The CLI monitor works in any terminal. The Qt GUI needs Linux GUI support from WSL.

Modern Windows 11 WSL installations usually include WSLg, which supports Linux GUI apps. If the GUI does not appear, verify that another Linux GUI app works before debugging this project.
