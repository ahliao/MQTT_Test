# Qt GUI Monitor

## Goal

The Qt GUI monitor is a visual version of the CLI monitor. It subscribes to the same MQTT topics, decodes the same protobuf messages, and displays the same latest sensor and processor values.

It also adds a live plot of voltage over time using `pyqtgraph`.

## What It Shows

- MQTT connection status
- Latest raw ADC value
- Latest raw voltage
- Latest moving average voltage
- Latest processor state such as `LOW`, `NORMAL`, or `HIGH`
- Live plot of raw voltage and moving average voltage

## Run It

Start Mosquitto first, then run the sensor and processor.

Run the GUI monitor with:

```bash
uv run python -m sensor_platform.monitor_qt --mqtt-host localhost
```

Or use the project script:

```bash
uv run sensor-platform-monitor-gui --mqtt-host localhost
```

## GUI Controls

- Plot channel: chooses which sensor/channel pair to plot.
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
```

Important files:

- `src/sensor_platform/monitor_qt.py`: main PySide6 window
- `src/sensor_platform/qt_mqtt_worker.py`: MQTT worker that emits Qt signals
- `src/sensor_platform/plot_history.py`: rolling data history for plots
- `src/sensor_platform/monitor_state.py`: latest values shared with the CLI monitor concept

## WSL Notes

The CLI monitor works in any terminal. The Qt GUI needs Linux GUI support from WSL.

Modern Windows 11 WSL installations usually include WSLg, which supports Linux GUI apps. If the GUI does not appear, verify that another Linux GUI app works before debugging this project.
