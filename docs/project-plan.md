# MQTT + Protobuf Sensor Platform Project Plan

## Goal

Build an educational Python project that demonstrates how an embedded Linux computer, such as a LattePanda IOTA, can collect sensor-like data, publish it over MQTT, process it, and monitor the system in real time.

The project should be easy to read, easy to run on WSL Ubuntu for development, and structured so each part teaches one concept clearly.

## Main Concepts

- MQTT publish/subscribe messaging
- Protocol Buffers for typed binary messages
- Simulated ADC sensor readings
- Separation between data producers, processors, and monitors
- Running multiple small Python services on Linux
- CLI monitoring for live sensor and processor data, with a clean path to a future GUI

## Proposed Architecture

```text
+------------------+        MQTT         +------------------+
| Simulated Sensor | -------------------> |    Processor     |
|                  | sensor/readings      |                  |
| Reads fake ADC   |                      | Computes derived |
| Encodes protobuf |                      | values/statistics|
+------------------+                      +--------+---------+
                                                     |
                                                     | MQTT
                                                     | processor/results
                                                     v
                                           +------------------+
                                           |     Monitor      |
                                           |                  |
                                           | CLI monitor      |
                                           | of both streams  |
                                           +------------------+

The monitor also subscribes directly to sensor/readings so it can display raw and processed data together.
```

## MQTT Topics

Use simple, explicit topics so the message flow is easy to understand.

| Topic | Publisher | Subscriber | Purpose |
| --- | --- | --- | --- |
| `sensor/adc/readings` | Sensor | Processor, Monitor | Raw simulated ADC readings |
| `processor/adc/results` | Processor | Monitor | Processed values and statistics |
| `platform/status` | All services, optional | Monitor | Startup, shutdown, and health messages |

## Protobuf Messages

Define messages in a single `.proto` file at first to keep the project approachable.

Proposed file: `proto/sensor_platform.proto`

Messages:

- `AdcReading`
- `ProcessedReading`
- `ServiceStatus`

Initial schema sketch:

```proto
syntax = "proto3";

package sensorplatform;

message AdcReading {
  string sensor_id = 1;
  int64 timestamp_ms = 2;
  uint32 channel = 3;
  uint32 raw_value = 4;
  double voltage = 5;
}

message ProcessedReading {
  string sensor_id = 1;
  int64 timestamp_ms = 2;
  uint32 channel = 3;
  double voltage = 4;
  double moving_average_voltage = 5;
  string state = 6;
}

message ServiceStatus {
  string service_name = 1;
  int64 timestamp_ms = 2;
  string status = 3;
  string message = 4;
}
```

## Project Parts

### 1. Sensor Service

Purpose: simulate a physical ADC connected to an embedded Linux board.

Responsibilities:

- Generate fake ADC readings on one or more channels
- Convert raw ADC counts to voltage
- Encode readings as protobuf messages
- Publish messages to MQTT topic `sensor/adc/readings`
- Print simple logs so the service is understandable while running

Educational focus:

- How sensor sampling loops work
- How raw ADC values map to voltage
- How protobuf serialization works
- How MQTT publishing works

Possible behavior:

- Simulate a slowly changing sine wave plus random noise
- Support command-line options for sensor ID, sample rate, MQTT host, and MQTT port
- Keep hardware-specific code isolated so a real ADC can be added later

### 2. Processor Service

Purpose: consume raw sensor readings and produce derived data.

Responsibilities:

- Subscribe to `sensor/adc/readings`
- Decode protobuf `AdcReading` messages
- Maintain a short moving average per sensor/channel
- Classify values into simple states such as `LOW`, `NORMAL`, or `HIGH`
- Publish protobuf `ProcessedReading` messages to `processor/adc/results`

Educational focus:

- How MQTT subscribers receive messages asynchronously
- How to deserialize protobuf payloads
- How to separate raw data from processed data
- How a simple stream processor can be built

### 3. Monitor Application

Purpose: display live raw and processed data.

Initial implementation: a readable CLI monitor.

The monitor should be designed so a GUI or terminal UI can be added later without rewriting the MQTT/protobuf logic. The key design choice is to keep message decoding and state storage separate from the display code.

Future GUI option: `Textual`, a terminal UI framework for Python.

Why Textual later:

- Easier to run on embedded Linux than a full desktop GUI
- Works over SSH
- More visual than plain CLI output
- Good for tables, panels, and live updates

Responsibilities:

- Subscribe to `sensor/adc/readings`
- Subscribe to `processor/adc/results`
- Decode protobuf messages
- Display latest raw ADC values, voltages, moving averages, and states
- Show connection/status information

Educational focus:

- How multiple MQTT topics can feed one monitor
- How real-time displays consume event streams
- How to keep UI code separate from message decoding

Future expansion:

- Add `monitor_tui.py` after the CLI monitor proves the message flow.
- Reuse shared monitor state and MQTT decoding code so the GUI layer only handles presentation.

## Proposed Directory Layout

```text
SensorPlatformTest/
├── docs/
│   └── project-plan.md
├── proto/
│   └── sensor_platform.proto
├── src/
│   └── sensor_platform/
│       ├── __init__.py
│       ├── config.py
│       ├── adc_simulator.py
│       ├── mqtt_client.py
│       ├── protobuf_helpers.py
│       ├── processor_logic.py
│       ├── sensor.py
│       ├── processor.py
│       ├── monitor_cli.py
│       ├── monitor_state.py
│       ├── generated/
│       │   └── sensor_platform_pb2.py
│       └── tools/
│           └── generate_protobuf.py
├── tests/
│   ├── test_adc_simulation.py
│   └── test_processor.py
├── pyproject.toml
└── README.md
```

## Dependencies

Runtime dependencies:

- `paho-mqtt` for MQTT client support
- `protobuf` for protobuf runtime support

Development dependencies:

- `grpcio-tools` for automatically generating Python protobuf modules
- `pytest` for tests
- `ruff` for formatting/linting, if desired

Python environment and package workflow:

- Use `uv` for creating the virtual environment, installing dependencies, running commands, and locking dependency versions.
- Add a separate document at `docs/uv-workflow.md` explaining the commands and mental model.

Protobuf generation:

- Generated protobuf Python files should not require a manual copy/paste step.
- Add the project command `uv run generate-protobuf` through a script entry in `pyproject.toml`.
- The command should read from `proto/sensor_platform.proto` and write generated Python code into `src/sensor_platform/generated/`.
- Document when to regenerate protobuf files: any time the `.proto` schema changes.

Infrastructure dependency:

- Mosquitto MQTT broker

Recommended local setup:

- Use WSL Ubuntu as the primary development environment.
- Install Mosquitto directly with Ubuntu packages instead of Docker.
- Document the same direct-install approach for embedded Linux.
- Keep `docs/docker-on-embedded-linux.md` as background tradeoff documentation, but Docker is not part of the initial implementation path.

## Execution Model

Each part should run as a separate Python command so the architecture is visible.

Example commands after implementation:

```bash
uv run python -m sensor_platform.sensor --mqtt-host localhost --sample-rate-hz 2
uv run python -m sensor_platform.processor --mqtt-host localhost
uv run python -m sensor_platform.monitor_cli --mqtt-host localhost
```

This makes it easy to open three terminals and observe the flow from sensor to processor to monitor.

## Implementation Milestones

### Milestone 1: Project Skeleton

- Create Python package layout
- Add `pyproject.toml`
- Add initial README
- Add protobuf schema
- Add automatic protobuf generation command
- Add `uv` workflow documentation

### Milestone 2: MQTT Broker Setup

- Document installing Mosquitto directly on WSL Ubuntu
- Document local broker startup with `systemctl` or direct `mosquitto` command options
- Verify publish/subscribe works with a simple test or manual command

### Milestone 3: Sensor Publisher

- Implement ADC simulator
- Implement voltage conversion
- Serialize `AdcReading` protobuf messages
- Publish readings over MQTT
- Add tests for ADC simulation and voltage conversion

### Milestone 4: Processor Subscriber/Publisher

- Subscribe to raw readings
- Decode protobuf messages
- Calculate moving average
- Classify sensor state
- Publish processed protobuf messages
- Add tests for moving average and state classification

### Milestone 5: Monitor

- Implement a simple CLI monitor first
- Keep monitor state separate from display code for later GUI/TUI expansion
- Show raw readings and processed readings together
- Display service status messages if implemented

### Milestone 6: Embedded Linux Notes

- Add instructions for running on a LattePanda IOTA or similar board
- Add system package notes
- Add Docker pros/cons as background only, not as the initial setup
- Add optional `systemd` service examples
- Document how a real ADC driver could replace the simulator

## Design Choices

### Keep Services Separate

Running the sensor, processor, and monitor as separate processes demonstrates the value of MQTT. Each part can start, stop, or fail independently.

### Use Protobuf Instead of JSON

Protobuf demonstrates typed messages, compact payloads, and explicit schemas. The code should include comments that make serialization and deserialization easy to follow.

### Use a Simulated ADC First

A simulator keeps the project runnable on any Linux machine. Hardware-specific code can be added later behind the same interface.

### Start With a CLI Monitor

The first monitor should be a CLI because it is easier to understand, easier to debug over SSH, and has fewer moving parts. The code should still be structured so a future Textual TUI or desktop GUI can reuse the same MQTT subscription and monitor-state logic.

### Use uv for Python Workflow

`uv` gives a modern Python workflow with fast dependency installs, virtual environment management, command running, and lockfiles. This project should use `uv` from the start so the setup is reproducible and educational.

### Avoid Docker Initially

Docker will not be used in the initial workflow. The project should be runnable on WSL Ubuntu by installing Mosquitto directly and running the Python services with `uv`. This keeps the learning path focused on Linux, MQTT, protobuf, and Python before adding container concepts.

### Generate Protobuf Files Automatically

The project should include a repeatable command for generating Python protobuf files. This avoids confusion about generated code and makes schema changes safer.

## Testing Strategy

Focus tests on pure logic first.

Test examples:

- Raw ADC value stays within expected range
- Raw ADC to voltage conversion is correct
- Moving average produces expected values
- State classifier returns `LOW`, `NORMAL`, or `HIGH` correctly
- Protobuf messages round-trip through serialization/deserialization

MQTT integration tests can be added later, but the first version should avoid making tests depend on a running broker.

## Documentation Goals

The README should eventually explain:

- What MQTT is doing in this project
- What protobuf is doing in this project
- How to install and start Mosquitto on WSL Ubuntu
- How automatic protobuf generation works
- How to run the sensor, processor, and monitor
- How to replace the simulated ADC with real hardware later

## Implementation Decisions

- Start with a CLI monitor, but structure the code so a GUI/TUI can be added easily.
- Generate protobuf Python files automatically with a project command.
- Use `uv` for the Python environment and dependency workflow.
- Make WSL Ubuntu the primary development environment.
- Do not use Docker in the initial implementation; install Mosquitto directly.
- Document Docker pros and cons only as background information.

## Recommended First Implementation Path

1. Create the Python package and `uv`-based dependency metadata.
2. Add the protobuf schema and automatic generation workflow.
3. Add the ADC simulator and unit tests.
4. Add MQTT publish/subscribe helpers.
5. Implement the sensor service.
6. Implement the processor service.
7. Implement a CLI monitor to verify the full message flow.
8. Add WSL Ubuntu setup instructions for Mosquitto and `uv`.
9. Add embedded Linux deployment notes, including Docker tradeoffs as background.
10. Optionally upgrade the monitor to a Textual TUI later.
