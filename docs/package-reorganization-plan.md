# Package Reorganization Plan

## Goal

Reorganize `src/sensor_platform/` so files are grouped by responsibility instead of mostly living at the package root.

The code should become easier to browse, easier to extend with new sensors/processors/monitors, and still remain beginner-friendly.

Status: implemented.

This document was originally written as a plan before the reorganization. It is now kept as a record of the target structure, migration reasoning, and verification checklist.

## Current Layout

```text
src/sensor_platform/
├── adc_simulator.py
├── config.py
├── generated/
├── gui_config.py
├── high_rate_batch.py
├── high_rate_processor.py
├── high_rate_sensor.py
├── monitor_cli.py
├── monitor_qt.py
├── monitor_state.py
├── mqtt_client.py
├── plot_history.py
├── processor_logic.py
├── processor.py
├── protobuf_helpers.py
├── qt_mqtt_worker.py
├── sensor.py
├── time_utils.py
└── tools/
```

Main issue:

- sensor code, processor code, monitor code, infrastructure code, and utility code are mixed together.

## Proposed Layout

```text
src/sensor_platform/
├── __init__.py
├── config.py
├── core/
│   ├── __init__.py
│   ├── mqtt_client.py
│   ├── protobuf_helpers.py
│   └── time_utils.py
├── generated/
│   ├── __init__.py
│   └── sensor_platform_pb2.py
├── gui/
│   ├── __init__.py
│   ├── config.py
│   ├── monitor_qt.py
│   ├── plot_history.py
│   └── qt_mqtt_worker.py
├── monitors/
│   ├── __init__.py
│   ├── monitor_cli.py
│   └── monitor_state.py
├── processors/
│   ├── __init__.py
│   ├── high_rate_processor.py
│   ├── processor.py
│   └── processor_logic.py
├── sensors/
│   ├── __init__.py
│   ├── adc_simulator.py
│   ├── high_rate_batch.py
│   ├── high_rate_sensor.py
│   └── sensor.py
└── tools/
    ├── __init__.py
    └── generate_protobuf.py
```

## Grouping Rationale

### `core/`

Shared infrastructure that multiple parts of the project use.

Move here:

- `mqtt_client.py`
- `protobuf_helpers.py`
- `time_utils.py`

Why:

- These are not sensors, processors, or monitors.
- They are shared support code.

### `sensors/`

Code that produces raw data.

Move here:

- `adc_simulator.py`
- `sensor.py`
- `high_rate_sensor.py`
- `high_rate_batch.py`

Why include `high_rate_batch.py` here:

- It generates high-rate raw sample batches.
- It also includes summary helpers currently used by the processor, so this could later be split if it grows.

Possible future split:

```text
sensors/high_rate_simulator.py
processors/high_rate_logic.py
```

For now, keep it in `sensors/` to avoid over-splitting.

### `processors/`

Code that consumes raw data and publishes processed data.

Move here:

- `processor.py`
- `processor_logic.py`
- `high_rate_processor.py`

Why:

- These files represent stream-processing services and processing math.

### `monitors/`

Non-GUI monitor code and shared monitor state.

Move here:

- `monitor_cli.py`
- `monitor_state.py`

Why:

- The CLI monitor is a monitor application.
- `monitor_state.py` is shared display state for monitor-style views.

### `gui/`

Qt-specific GUI code.

Move here:

- `monitor_qt.py`
- `qt_mqtt_worker.py`
- `plot_history.py`
- `gui_config.py`, renamed to `config.py`

Why:

- These files are specific to the GUI monitor.
- Keeping Qt and pyqtgraph code isolated makes the rest of the project easier to understand.

### `generated/`

Keep as-is.

Why:

- Generated protobuf files are already separated.
- They should not be mixed with handwritten code.

### `tools/`

Keep as-is.

Why:

- Project maintenance commands are already separated.

## Updated Script Entry Points

Update `pyproject.toml` from:

```toml
sensor-platform-sensor = "sensor_platform.sensor:main"
sensor-platform-high-rate-sensor = "sensor_platform.high_rate_sensor:main"
sensor-platform-processor = "sensor_platform.processor:main"
sensor-platform-high-rate-processor = "sensor_platform.high_rate_processor:main"
sensor-platform-monitor = "sensor_platform.monitor_cli:main"
sensor-platform-monitor-gui = "sensor_platform.monitor_qt:main"
```

To:

```toml
sensor-platform-sensor = "sensor_platform.sensors.sensor:main"
sensor-platform-high-rate-sensor = "sensor_platform.sensors.high_rate_sensor:main"
sensor-platform-processor = "sensor_platform.processors.processor:main"
sensor-platform-high-rate-processor = "sensor_platform.processors.high_rate_processor:main"
sensor-platform-monitor = "sensor_platform.monitors.monitor_cli:main"
sensor-platform-monitor-gui = "sensor_platform.gui.monitor_qt:main"
```

Keep:

```toml
generate-protobuf = "sensor_platform.tools.generate_protobuf:main"
```

## Import Update Examples

Examples of imports that would change:

```python
from sensor_platform.mqtt_client import create_client
```

Becomes:

```python
from sensor_platform.core.mqtt_client import create_client
```

```python
from sensor_platform.adc_simulator import SimulatedAdc
```

Becomes:

```python
from sensor_platform.sensors.adc_simulator import SimulatedAdc
```

```python
from sensor_platform.processor_logic import MovingAverage
```

Becomes:

```python
from sensor_platform.processors.processor_logic import MovingAverage
```

```python
from sensor_platform.plot_history import HighRatePlotHistory
```

Becomes:

```python
from sensor_platform.gui.plot_history import HighRatePlotHistory
```

## Test Reorganization

Two options are reasonable.

### Option A: Keep Tests Flat

```text
tests/
├── test_adc_simulator.py
├── test_gui_config.py
├── test_high_rate_batch.py
├── test_plot_history.py
├── test_processor_logic.py
└── test_protobuf_helpers.py
```

Pros:

- Simple.
- No test discovery changes.
- Good for a small educational project.

Cons:

- Test folder does not mirror source structure.

### Option B: Mirror Source Structure

```text
tests/
├── core/
│   └── test_protobuf_helpers.py
├── gui/
│   ├── test_gui_config.py
│   └── test_plot_history.py
├── processors/
│   └── test_processor_logic.py
└── sensors/
    ├── test_adc_simulator.py
    └── test_high_rate_batch.py
```

Pros:

- Scales better as the project grows.
- Easier to find tests matching a package.

Cons:

- More directories for a beginner to navigate.

Recommendation:

- Use Option B because the goal is to make the project easier to grow.

## Documentation Updates Needed

Update code references in:

- `README.md`
- `docs/adding-sensors-processors-plots.md`
- `docs/high-rate-sensor-batching.md`
- `docs/qt-gui-monitor.md`
- `docs/package-reorganization-plan.md` if implementation differs from this plan

Command examples do not need to change if script entry points are updated correctly.

Existing commands should still work:

```bash
uv run sensor-platform-sensor
uv run sensor-platform-high-rate-sensor
uv run sensor-platform-processor
uv run sensor-platform-high-rate-processor
uv run sensor-platform-monitor
uv run sensor-platform-monitor-gui
```

Direct module commands would change.

Old:

```bash
uv run python -m sensor_platform.sensor
```

New:

```bash
uv run python -m sensor_platform.sensors.sensor
```

## Migration Order

Use a small-step migration to avoid breaking everything at once.

1. Create new package directories with `__init__.py` files.
2. Move `core` files and update imports.
3. Move sensor files and update imports/tests.
4. Move processor files and update imports/tests.
5. Move monitor and GUI files and update imports/tests.
6. Update `pyproject.toml` script entry points.
7. Update docs that reference old module paths.
8. Run `uv run pytest`.
9. Run `uv run ruff check .`.
10. Run script help commands for all entry points.

## Compatibility Choice

Do not keep old wrapper modules unless there is a concrete need.

Reason:

- This project is still local and educational.
- There are no external consumers relying on imports like `sensor_platform.sensor`.
- Avoiding wrappers keeps the package cleaner.

If backward-compatible direct module commands are desired later, small wrapper files could be added, but they are not recommended for this cleanup.

## Verification Checklist

After implementation, verify:

```bash
uv run generate-protobuf
uv run pytest
uv run ruff check .
uv run sensor-platform-sensor --help
uv run sensor-platform-high-rate-sensor --help
uv run sensor-platform-processor --help
uv run sensor-platform-high-rate-processor --help
uv run sensor-platform-monitor --help
uv run sensor-platform-monitor-gui --help
```

Also verify imports:

```bash
uv run python -c "import sensor_platform.sensors.sensor"
uv run python -c "import sensor_platform.processors.processor"
uv run python -c "import sensor_platform.gui.monitor_qt"
```

## Recommended Final Structure

The recommended structure is:

```text
src/sensor_platform/
├── config.py                  # shared constants and topic names
├── core/                      # MQTT/protobuf/time infrastructure
├── generated/                 # generated protobuf code
├── gui/                       # PySide6 GUI monitor
├── monitors/                  # CLI monitor and monitor state
├── processors/                # processor services and logic
├── sensors/                   # sensor services and simulators
└── tools/                     # project maintenance commands
```

This keeps the top-level package small while making each major concept visible.
