# WSL Ubuntu Setup

## Goal

Run the full sensor platform on WSL Ubuntu without Docker.

You will run:

- Mosquitto MQTT broker installed directly from Ubuntu packages
- Python services managed by `uv`
- Three separate processes: sensor, processor, and monitor

## Install System Packages

Update Ubuntu package metadata:

```bash
sudo apt update
```

Install Mosquitto and command-line MQTT clients:

```bash
sudo apt install mosquitto mosquitto-clients
```

The `mosquitto-clients` package gives you `mosquitto_pub` and `mosquitto_sub`, which are useful for learning and debugging MQTT.

For the PySide6 GUI monitor, WSL also needs the basic OpenGL/runtime libraries used by Qt:

```bash
sudo apt install libgl1 libegl1 libxkbcommon-x11-0
```

## Start Mosquitto

Many WSL Ubuntu installations support `systemd`. If yours does, start Mosquitto with:

```bash
sudo systemctl start mosquitto
```

Check its status with:

```bash
systemctl status mosquitto
```

If your WSL Ubuntu instance does not use `systemd`, run Mosquitto directly in its own terminal:

```bash
mosquitto -v
```

Leave that terminal open while running the project.

## Verify MQTT Manually

Open one terminal and subscribe to a test topic:

```bash
mosquitto_sub -h localhost -t test/topic
```

Open another terminal and publish a test message:

```bash
mosquitto_pub -h localhost -t test/topic -m "hello mqtt"
```

The subscriber terminal should print:

```text
hello mqtt
```

## Install uv

If `uv` is not already installed, follow the official installation instructions at:

```text
https://docs.astral.sh/uv/getting-started/installation/
```

After installing, verify it is available:

```bash
uv --version
```

## Prepare the Python Environment

From the project directory, run:

```bash
uv sync
```

This creates or updates the project virtual environment and installs dependencies.

## Generate Protobuf Code

Run:

```bash
uv run generate-protobuf
```

This generates Python code from `proto/sensor_platform.proto`.

## Run Tests

Run:

```bash
uv run pytest
```

## Run the Platform

Open three terminals in the project directory.

Terminal 1, run the sensor:

```bash
uv run python -m sensor_platform.sensor --mqtt-host localhost --sample-rate-hz 2
```

Terminal 2, run the processor:

```bash
uv run python -m sensor_platform.processor --mqtt-host localhost
```

Terminal 3, run the monitor:

```bash
uv run python -m sensor_platform.monitor_cli --mqtt-host localhost
```

You should see the sensor publishing raw ADC values, the processor publishing moving averages, and the monitor showing the latest values.

## Run the GUI Monitor

If your Windows and WSL setup supports Linux GUI apps, you can run the PySide6 monitor instead of the CLI monitor:

```bash
uv run python -m sensor_platform.monitor_qt --mqtt-host localhost
```

The GUI shows the same latest raw and processed values as the CLI monitor, plus a live voltage plot using `pyqtgraph`.

If the GUI does not open, first confirm that a simple WSL Linux GUI app works on your machine. WSLg is included with modern Windows 11 WSL installs, but older setups may need additional display server configuration.
