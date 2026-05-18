# Sensor Platform Test

Educational Python project demonstrating MQTT and protobuf in a small sensor platform.

The project is designed to run first on WSL Ubuntu for development, then later on an embedded Linux computer such as a LattePanda IOTA.

## What It Demonstrates

- A simulated ADC sensor that publishes readings over MQTT
- A processor that subscribes to raw readings and publishes derived results
- A CLI monitor that displays raw and processed data
- A PySide6 GUI monitor with a live pyqtgraph voltage plot
- A high-rate sensor example that packages many ADC samples into one protobuf MQTT message
- Protobuf message schemas and generated Python message classes
- `uv` for Python dependency and command management
- Direct Mosquitto setup without Docker

## Services

Sensor publisher:

```bash
uv run python -m sensor_platform.sensors.sensor --mqtt-host localhost --sample-rate-hz 2
```

Processor:

```bash
uv run python -m sensor_platform.processors.processor --mqtt-host localhost
```

CLI monitor:

```bash
uv run python -m sensor_platform.monitors.monitor_cli --mqtt-host localhost
```

GUI monitor:

```bash
uv run python -m sensor_platform.gui.monitor_qt --mqtt-host localhost
```

To keep a longer high-rate capture visible, set the rolling high-rate plot window:

```bash
uv run sensor-platform-monitor-gui --high-rate-window-seconds 10
```

High-rate sensor publisher:

```bash
uv run sensor-platform-high-rate-sensor --sample-rate-hz 10000 --batch-size 500
```

High-rate processor:

```bash
uv run sensor-platform-high-rate-processor
```

Open three WSL Ubuntu terminals and run the sensor, processor, and either monitor.

## MQTT Topics

| Topic | Publisher | Subscriber | Purpose |
| --- | --- | --- | --- |
| `sensor/adc/readings` | Sensor | Processor, Monitor | Raw ADC readings |
| `processor/adc/results` | Processor | Monitor | Moving average and state |
| `sensor/adc/high-rate/batches` | High-rate sensor | High-rate processor | Batched raw ADC samples |
| `processor/adc/high-rate/results` | High-rate processor | GUI monitor | Summary and downsampled batch data |

## Setup Summary

See `docs/wsl-ubuntu-setup.md` for the full WSL Ubuntu setup.

Short version:

```bash
sudo apt update
sudo apt install mosquitto mosquitto-clients
uv sync
uv run generate-protobuf
uv run pytest
```

## Protobuf Generation

The `.proto` schema lives at:

```text
proto/sensor_platform.proto
```

Generate Python protobuf code with:

```bash
uv run generate-protobuf
```

Generated files are written under:

```text
src/sensor_platform/generated/
```

Regenerate protobuf files any time `proto/sensor_platform.proto` changes.

## Documentation

- `docs/project-plan.md`: project plan and implementation direction
- `docs/pyproject-explained.md`: beginner explanation of `pyproject.toml`
- `docs/uv-workflow.md`: how `uv` works in this project
- `docs/protobuf-overview.md`: protobuf explanation and tradeoffs
- `docs/wsl-ubuntu-setup.md`: WSL Ubuntu setup instructions
- `docs/qt-gui-monitor.md`: PySide6 GUI monitor usage
- `docs/high-rate-sensor-batching.md`: high-rate protobuf batching example
- `docs/adding-sensors-processors-plots.md`: how to extend the project with new streams
- `docs/remote-mqtt-monitoring.md`: secure remote MQTT broker setup
- `docs/docker-on-embedded-linux.md`: Docker tradeoffs for later consideration
