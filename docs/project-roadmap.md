# Project Roadmap

## Goal

Evolve this project from an educational MQTT/protobuf demo into a practical embedded sensor platform that is still easy to understand and extend.

The next phase should focus on four areas:

- Make the GUI easier to extend without editing the main window for every new stream.
- Add reusable sensor templates for common hardware interfaces.
- Support native Rust or C++ sensor publishers for high-speed acquisition.
- Improve deployment and hardware setup documentation for embedded Linux systems.

## Guiding Principles

- Keep MQTT and protobuf as the language-neutral boundary between services.
- Keep hardware-specific code isolated from message schemas, processing logic, and GUI display code.
- Prefer small runnable examples over large frameworks.
- Make every new sensor template include a simulator or test mode when possible.
- Keep Python as the orchestration and GUI layer, but allow Rust or C++ where acquisition speed or driver libraries require it.
- Document operational setup as part of each hardware interface, not as an afterthought.

## Progress

Current roadmap status:

| Area | Status | Notes |
| --- | --- | --- |
| Phase 1.1: Stream Registry | Complete | Added shared stream registry, stream listing command, tests, and docs. |
| Phase 1.2: Service Template Pattern | Complete | Added shared CLI/logging helpers, refactored existing services, added tests, and documented service skeletons. |
| Phase 1.3: Message Design Guidelines | Complete | Added topic, protobuf field, compatibility, batch, status, and native publisher guidelines. |
| Phase 2: More Flexible GUI | Not started | Depends on the stream registry and benefits from service/template consistency. |
| Phase 3: Sensor Templates | Not started | UART/replay templates should come after Phase 1.2. |
| Phase 4: Rust and C++ Sensor Support | Not started | Native examples should reuse the same stream/message contracts. |
| Phase 5: Embedded Linux Operations Docs | In progress | LattePanda boot setup exists; udev and Ethernet docs still needed. |
| Phase 6: Observability, Reliability, and Testing | Not started | Status messages and replay tools are future work. |

## Phase 1: Extension Foundation

Purpose: make the current Python project easier to expand before adding many new sensor types.

### 1.1 Stream Registry

Status: complete.

Create a central stream registry that describes raw topics, processed topics, protobuf parsers, display labels, and default visualization hints.

Implemented files:

```text
src/sensor_platform/streams.py
src/sensor_platform/tools/list_streams.py
tests/core/test_streams.py
```

Completed work:

- Moved stream metadata into a shared registry usable by GUI, docs, tests, and future tools.
- Keep parser functions in `src/sensor_platform/core/protobuf_helpers.py`.
- Added `uv run sensor-platform-list-streams` for registry inspection.
- Added tests for unique stream names, unique topics, parser presence, lookups, and default visibility.
- Refactored GUI config to consume the shared registry.

Deliverables:

- `src/sensor_platform/streams.py`
- `sensor-platform-list-streams`
- `tests/core/test_streams.py`
- Documentation updates in `docs/adding-sensors-processors-plots.md` and `docs/qt-gui-monitor.md`

### 1.2 Service Template Pattern

Status: complete.

Create a consistent shape for new sensor and processor services.

Implemented files:

```text
src/sensor_platform/core/cli.py
src/sensor_platform/core/service_logging.py
tests/core/test_cli.py
docs/service-template-pattern.md
```

Completed work:

- Added shared MQTT, sensor identity, logging, and validation CLI helpers.
- Added shared service logging configuration.
- Refactored low-rate and high-rate sensor services to use the helpers.
- Refactored low-rate and high-rate processor services to use the helpers.
- Added tests for CLI helper behavior and validation errors.
- Added documented sensor and processor skeletons.
- Updated extension docs to point new services toward the shared pattern.

Implementation plan: `docs/phase-1-2-service-template-plan.md`.

Deliverables:

- A documented sensor service skeleton.
- A documented processor service skeleton.
- Shared command-line options for MQTT host, port, sensor ID, and logging level.
- Tests for pure processing logic before MQTT integration.

Avoid turning this into a heavy base-class framework early. Start with simple helper functions and clear examples.

### 1.3 Message Design Guidelines

Status: complete.

Expand protobuf documentation with concrete schema patterns.

Implemented files:

```text
docs/message-design-guidelines.md
```

Completed work:

- Added MQTT topic naming conventions.
- Added protobuf message and field naming conventions.
- Documented timestamp and unit naming rules.
- Documented field-number compatibility and reserved-field guidance.
- Added low-rate sample and high-rate batch schema patterns.
- Added status and error message patterns.
- Added native Rust/C++ publisher compatibility guidance.
- Linked the guide from protobuf and extension documentation.

Deliverables:

- Naming conventions for topics and protobuf messages.
- Guidance for low-rate samples, batched high-rate samples, device status, and error messages.
- Rules for units in field names, timestamp units, and field-number compatibility.

## Phase 2: More Flexible GUI

Purpose: let users add new views with minimal changes to the main GUI.

### 2.1 Pluggable Display Panels

Split GUI display handling into small panel classes or functions by stream type.

Candidate panel types:

- Latest-value table panel
- Time-series plot panel
- Batched waveform plot panel
- Spectrum or FFT panel
- Device status panel
- Log/event panel

Deliverables:

- A panel interface that receives decoded stream messages.
- Separate low-rate ADC and high-rate ADC panel implementations.
- Main window that loads panels from stream metadata instead of hardcoding every stream handler.

### 2.2 User-Facing Stream Configuration

Add a simple configuration file for GUI layout and stream visibility.

Possible format:

```toml
[[streams]]
name = "adc-low-rate"
visible = true
panel = "time-series"

[[streams]]
name = "adc-high-rate"
visible = true
panel = "batch-waveform"
```

Deliverables:

- Default GUI config checked into the project.
- Command-line option such as `--gui-config config/gui.toml`.
- Clear error messages when a configured stream or panel is unknown.

### 2.3 GUI Usability Improvements

Improve the monitor for real use on a development PC.

Deliverables:

- Connection status per stream.
- Last-message age per stream.
- Pause/resume per plot, not only globally.
- Configurable plot windows and downsample limits.
- Export recent data to CSV for debugging.

## Phase 3: Sensor Templates

Purpose: provide practical starting points for real hardware interfaces.

Each template should include a runnable service, simulated/test mode, setup documentation, and at least one focused test for parsing or processing logic.

### 3.1 UART Sensor Template

Use cases:

- GPS modules
- Microcontroller serial streams
- RS-232/RS-485 adapters
- Simple ASCII or binary packet sensors

Recommended Python dependency:

```text
pyserial
```

Deliverables:

- `src/sensor_platform/sensors/uart_sensor_template.py`
- Serial packet parser example.
- CLI options for `--serial-port`, `--baud-rate`, `--timeout-s`.
- Documentation for finding serial devices and setting permissions.

Related docs to add:

- `docs/uart-sensor-setup.md`
- `docs/udev-usb-rules.md`

### 3.2 USB Sensor Template

Use cases:

- USB HID sensors
- USB CDC serial devices
- Vendor SDK devices
- USB data acquisition modules

Recommended starting point:

- Treat USB CDC devices as UART first.
- Add raw USB or vendor SDK examples only when a concrete device is selected.

Deliverables:

- USB device discovery notes using `lsusb`, `dmesg`, and `/dev/serial/by-id/`.
- udev rule examples for stable names and permissions.
- A template that reads from a stable `/dev/sensor-*` symlink.

### 3.3 Ethernet Sensor Template

Use cases:

- TCP sensors
- UDP streaming sensors
- Modbus TCP devices
- Ethernet DAQ hardware

Deliverables:

- `src/sensor_platform/sensors/ethernet_sensor_template.py`
- CLI options for `--sensor-host`, `--sensor-port`, and protocol mode.
- TCP request/response example.
- UDP listener example if needed.
- Documentation for static IP setup and direct laptop-to-sensor networking.

Related docs to add:

- `docs/ethernet-sensor-networking.md`
- `docs/static-ip-setup.md`

### 3.4 File and Replay Sensor Template

Use cases:

- Replaying captured test data.
- Developing processors and GUI panels without hardware.

Deliverables:

- CSV or JSONL replay publisher.
- Adjustable replay speed.
- Sample data files under a small `examples/` or `sample_data/` directory.

This should come before complex hardware support because it improves testing and demos.

## Phase 4: Rust and C++ Sensor Support

Purpose: support high-speed or hardware-specific sensors while keeping the rest of the platform language-neutral.

### 4.1 Define the Cross-Language Contract

The contract should remain:

- MQTT topics for transport.
- Protobuf messages for payloads.
- Shared `.proto` schema as the source of truth.
- Compatible timestamps, units, and topic names across languages.

Deliverables:

- `docs/native-sensor-integration.md`
- Build instructions for generating protobuf code for Python, Rust, and C++.
- A compatibility test plan that publishes sample payloads and verifies Python can parse them.

### 4.2 Rust Publisher Example

Use Rust for a first native example because it has strong package management and good async/networking options.

Candidate libraries:

- `prost` for protobuf generation.
- `rumqttc` for MQTT.
- `serialport` for UART when needed.

Deliverables:

- `native/rust/` example publisher.
- Build command documented with `cargo build`.
- Example command that publishes to the same MQTT topics as Python.
- Python test or utility that verifies the Rust-published payload.

### 4.3 C++ Publisher Example

Use C++ when integrating vendor SDKs, camera/DAQ APIs, or existing real-time acquisition code.

Candidate libraries:

- Official protobuf C++ runtime.
- Eclipse Paho MQTT C++ or another maintained MQTT client.
- CMake for build configuration.

Deliverables:

- `native/cpp/` example publisher.
- CMake build instructions.
- Minimal low-rate publisher first, then high-rate batch publisher.
- Documentation for linking vendor SDK libraries later.

### 4.4 Native Service Deployment

Add systemd examples for native publishers.

Deliverables:

- systemd unit examples for Rust and C++ binaries.
- Logging guidance for native services.
- Notes on CPU affinity or process priority only after there is a measured need.

## Phase 5: Embedded Linux Operations Documentation

Purpose: make setup repeatable on LattePanda IOTA and similar Ubuntu systems.

### 5.1 udev USB Rules

Add a focused guide for stable USB device names and permissions.

Must cover:

- Finding vendor and product IDs with `lsusb`.
- Watching device attach logs with `dmesg` or `journalctl -k`.
- Creating `/etc/udev/rules.d/99-sensor-platform.rules`.
- Creating stable symlinks such as `/dev/sensor-gps`.
- Adding the service user to groups such as `dialout` when appropriate.
- Reloading rules with `sudo udevadm control --reload-rules` and `sudo udevadm trigger`.

### 5.2 Ethernet and Static IP Setup

Add docs for sensors that require direct Ethernet or fixed IP networks.

Must cover:

- Finding the IOTA network interface name.
- Configuring static IPs with Ubuntu networking tools.
- Testing with `ping`, `nc`, or device-specific utilities.
- Keeping the sensor network separate from internet/Wi-Fi when needed.
- Firewall considerations for MQTT and sensor ports.

### 5.3 Service Management

Expand the LattePanda boot setup docs as more services appear.

Must cover:

- One unit per long-running service.
- Service dependencies on `mosquitto.service` and `network-online.target`.
- Environment files for per-device settings.
- Log inspection with `journalctl`.
- Safe update procedure using `systemctl stop`, `git pull`, `uv sync`, tests, then restart.

### 5.4 Hardware Troubleshooting Guides

Add concise checklists by interface type.

Examples:

- UART: wrong baud rate, permissions, newline framing, disconnected adapter.
- USB: unstable device path, missing udev rule, power limits, vendor driver missing.
- Ethernet: wrong subnet, firewall, duplicate IP, device not listening.
- High-rate: CPU saturation, message size too large, GUI plotting too many points.

## Phase 6: Observability, Reliability, and Testing

Purpose: make the platform easier to debug as more services and languages are added.

### 6.1 Service Status Messages

Add a `ServiceStatus` protobuf flow if it is not already implemented.

Deliverables:

- Common status topic such as `platform/status`.
- Startup, heartbeat, warning, and shutdown messages.
- GUI status panel that shows service health.

### 6.2 Recording and Replay

Add a way to record MQTT payloads and replay them.

Deliverables:

- Recorder utility for selected topics.
- Replay utility that republishes with original or adjusted timing.
- Example recorded datasets for GUI and processor tests.

### 6.3 Contract Tests

Add tests that protect language and service compatibility.

Deliverables:

- Golden protobuf payloads.
- Tests that parse payloads produced by Python, Rust, and C++ examples.
- Topic registry validation tests.
- GUI parser configuration tests.

## Suggested Implementation Order

1. Build the shared stream registry and update the GUI to consume it.
2. Refactor GUI panels so new stream displays do not require editing the whole main window.
3. Add file/replay sensor support to improve demos and testing.
4. Add UART template and udev documentation.
5. Add Ethernet template and static IP documentation.
6. Add Rust publisher example using the existing high-rate batch protobuf message.
7. Add C++ publisher example after the Rust path proves the native integration pattern.
8. Add status messages, recording, replay, and contract tests.

## Near-Term Milestones

### Milestone A: Extensible GUI Base

Success criteria:

- Existing low-rate and high-rate displays still work.
- New streams can be registered without changing MQTT worker code.
- At least one display panel is split out of `monitor_qt.py`.

### Milestone B: First Real Interface Template

Success criteria:

- UART template can read simulated or loopback serial data.
- udev documentation explains stable device names.
- Template publishes protobuf messages to MQTT.

### Milestone C: Native High-Speed Publisher

Success criteria:

- Rust service publishes protobuf batches to MQTT.
- Existing Python high-rate processor and GUI can consume the Rust messages unchanged.
- Build and run instructions are documented.

### Milestone D: Embedded Deployment Kit

Success criteria:

- LattePanda boot docs cover Python and native services.
- Ethernet and USB setup docs exist.
- Troubleshooting docs cover common setup failures.

## Open Decisions

- Whether GUI stream layout should use TOML, YAML, JSON, or Python config.
- Whether native examples should live in this repository or separate repositories.
- Whether high-speed native publishers should publish directly to MQTT or use a local bridge process.
- Which real sensor should be the first hardware-backed example.
- Whether to add authentication support to all MQTT clients before expanding remote deployment examples.
