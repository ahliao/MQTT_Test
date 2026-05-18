# AGENTS.md

## Commands

- Use `uv sync` after changing `pyproject.toml` entry points or dependencies.
- Run `uv run generate-protobuf` after any change to `proto/sensor_platform.proto`; generated output belongs in `src/sensor_platform/generated/`.
- Run focused tests with `uv run pytest tests/<subdir-or-file>.py`; full suite is `uv run pytest`.
- Run lint with `uv run ruff check .`.
- Verify service entry points with `uv run <script> --help`, especially after moving modules.

## Package Layout

- `src/sensor_platform/core/`: shared MQTT, protobuf, and time helpers.
- `src/sensor_platform/sensors/`: sensor publishers, ADC simulator, and high-rate batch helpers.
- `src/sensor_platform/processors/`: processor services and pure processing logic.
- `src/sensor_platform/monitors/`: CLI monitor and shared monitor state.
- `src/sensor_platform/gui/`: PySide6 GUI, GUI stream config, Qt MQTT worker, and plot history.
- `src/sensor_platform/generated/`: generated protobuf code; do not edit manually.

## Entry Points

- Scripts in `pyproject.toml` are the preferred run commands; direct module paths are nested after the reorg.
- Low-rate path: `sensor-platform-sensor` -> `sensor-platform-processor` -> `sensor-platform-monitor` or `sensor-platform-monitor-gui`.
- High-rate path: `sensor-platform-high-rate-sensor` -> `sensor-platform-high-rate-processor` -> `sensor-platform-monitor-gui`.

## MQTT And Protobuf

- MQTT topics are constants in `src/sensor_platform/config.py`; protobuf message contracts are in `proto/sensor_platform.proto`.
- Keep protobuf parse helpers in `src/sensor_platform/core/protobuf_helpers.py` rather than parsing payloads inline.
- The high-rate example batches many ADC samples into one protobuf message; do not change it to one MQTT message per sample.

## GUI Notes

- GUI MQTT subscriptions/parsers are configured in `src/sensor_platform/gui/config.py` via `GUI_STREAMS`.
- `src/sensor_platform/gui/qt_mqtt_worker.py` should stay generic: subscribe from config, parse by topic, emit decoded messages.
- `src/sensor_platform/gui/monitor_qt.py` still owns display-specific table/plot handlers.
- High-rate plot history smooths unrealistic wall-clock timestamp gaps for the simulator; see `HighRatePlotHistory` before changing timing behavior.

## Test Layout

- Tests mirror source groups: `tests/core/`, `tests/gui/`, `tests/processors/`, `tests/sensors/`.
- Prefer testing pure logic without a running MQTT broker; current tests do not require Mosquitto.

## Environment

- Development target is WSL Ubuntu with Mosquitto installed directly, not Docker.
- Running live services requires a Mosquitto broker; unit tests and lint do not.
