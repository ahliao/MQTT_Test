# Phase 1.2 Service Template Pattern Plan

Status: complete.

Implemented deliverables:

- `src/sensor_platform/core/cli.py`
- `src/sensor_platform/core/service_logging.py`
- `tests/core/test_cli.py`
- `docs/service-template-pattern.md`
- Existing sensor and processor services refactored to use shared helpers.

## Goal

Create a consistent, documented pattern for adding new sensor and processor services without introducing a heavy framework.

This phase should make future UART, USB, Ethernet, replay, Rust, and C++ work easier by standardizing the Python service shape first.

## Current Problem

The existing services work, but each service owns its own small variations of common behavior:

- MQTT host and port command-line options
- sensor ID options
- sample rate validation
- startup and shutdown logging
- MQTT connect/disconnect lifecycle
- processor subscription setup
- invalid payload handling

This is manageable with the current ADC examples, but it will become repetitive as more sensor templates are added.

## Non-Goals

Do not build a large service framework in this phase.

Avoid:

- abstract base classes for every service
- plugin loading
- dynamic imports
- YAML/TOML service definitions
- async rewrites
- changing the MQTT/protobuf contract
- changing GUI panel behavior

The target is simple shared helpers plus clear skeletons.

## Desired Service Shape

Every Python sensor service should follow this shape:

1. Define `build_parser()`.
2. Add shared MQTT/logging options.
3. Add service-specific options.
4. Validate arguments near startup.
5. Create or open the hardware/simulator source.
6. Connect to MQTT.
7. Publish protobuf messages in a clear loop.
8. Cleanly stop MQTT and hardware resources.

Every Python processor service should follow this shape:

1. Define `build_parser()`.
2. Add shared MQTT/logging options.
3. Add processor-specific options.
4. Keep pure processing logic outside MQTT callbacks when practical.
5. Connect to MQTT.
6. Subscribe in `on_connect()`.
7. Parse payloads with helpers from `core/protobuf_helpers.py`.
8. Publish processed protobuf messages.
9. Handle invalid payloads without crashing the service.

## Proposed Implementation

### 1. Add Shared CLI Helpers

Create:

```text
src/sensor_platform/core/cli.py
```

Add small helper functions:

```python
def add_mqtt_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--mqtt-host", default=MQTT_HOST)
    parser.add_argument("--mqtt-port", type=int, default=MQTT_PORT)


def add_sensor_identity_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--sensor-id", default=DEFAULT_SENSOR_ID)
    parser.add_argument("--channel", type=int, default=DEFAULT_CHANNEL)


def add_logging_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])
```

Keep these helpers boring and explicit. They should only add arguments; they should not parse args or start services.

### 2. Add Validation Helpers

Also in `core/cli.py`, add small validation helpers if they remove duplication cleanly.

Candidate helpers:

```python
def require_positive_float(value: float, option_name: str) -> None:
    if value <= 0:
        raise SystemExit(f"{option_name} must be greater than 0")


def require_positive_int(value: int, option_name: str) -> None:
    if value <= 0:
        raise SystemExit(f"{option_name} must be greater than 0")
```

Use them only where they make existing code clearer.

### 3. Standardize Logging Setup

Move new services toward Python `logging`, while keeping changes to existing services minimal.

Add:

```text
src/sensor_platform/core/logging.py
```

Possible helper:

```python
def configure_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
```

Phase 1.2 should not require converting every existing `print()` immediately. A minimal first pass can add the helper and use it in the new skeletons.

### 4. Add Documented Sensor Skeleton

Create a template document section or example file showing a low-rate sensor service skeleton.

Preferred path:

```text
docs/service-template-pattern.md
```

The skeleton should show:

- shared MQTT arguments
- shared sensor identity arguments
- service-specific arguments
- argument validation
- MQTT client lifecycle
- protobuf construction
- publishing loop
- clean shutdown

Do not add a generated template system yet. A readable copyable skeleton is enough.

### 5. Add Documented Processor Skeleton

In the same doc, add a processor skeleton showing:

- shared MQTT arguments
- processor-specific options
- `on_connect()` subscription
- `on_message()` parsing
- invalid payload handling
- pure logic call
- processed protobuf publishing

The processor skeleton should explicitly recommend putting math/state logic in a separate module with tests.

### 6. Refactor Existing Services Lightly

Update existing Python services to use shared CLI helpers where it reduces duplication.

Good first targets:

- `src/sensor_platform/sensors/sensor.py`
- `src/sensor_platform/sensors/high_rate_sensor.py`
- `src/sensor_platform/processors/processor.py`
- `src/sensor_platform/processors/high_rate_processor.py`

Expected changes:

- replace repeated `--mqtt-host` and `--mqtt-port` declarations with `add_mqtt_arguments(parser)`
- replace repeated sensor ID/channel declarations where applicable
- replace positive value checks with validation helpers if clearer

Avoid changing runtime behavior.

### 7. Add Tests

Add tests for shared helpers:

```text
tests/core/test_cli.py
```

Test cases:

- `add_mqtt_arguments()` adds default host and port.
- `add_sensor_identity_arguments()` adds default sensor ID and channel.
- positive float validation accepts valid values.
- positive float validation rejects zero and negative values.
- positive int validation accepts valid values.
- positive int validation rejects zero and negative values.

If logging setup is added, keep tests minimal or skip direct logging tests unless behavior is important.

### 8. Update Existing Extension Docs

Update:

```text
docs/adding-sensors-processors-plots.md
```

The checklist should mention:

- use shared CLI helpers from `core/cli.py`
- put pure processing logic in a testable module
- register streams in `streams.py`
- add tests before adding GUI display handling

## Recommended Implementation Order

1. Add `core/cli.py` with argument and validation helpers.
2. Add tests for `core/cli.py`.
3. Refactor one low-rate sensor to use the helpers.
4. Refactor one processor to use the helpers.
5. Refactor high-rate services if the changes stay mechanical.
6. Add `docs/service-template-pattern.md` with sensor and processor skeletons.
7. Update `docs/adding-sensors-processors-plots.md` to reference the template pattern.
8. Run focused tests, full tests, lint, and service `--help` checks.

## Verification Commands

Run:

```bash
uv run pytest tests/core/test_cli.py
uv run pytest tests/sensors tests/processors tests/core
uv run ruff check .
```

Verify service entry points still expose the same user-facing options:

```bash
uv run sensor-platform-sensor --help
uv run sensor-platform-high-rate-sensor --help
uv run sensor-platform-processor --help
uv run sensor-platform-high-rate-processor --help
```

## Definition of Done

Phase 1.2 is complete when:

- Shared CLI helpers exist for common MQTT and sensor identity options.
- Validation helpers remove repeated positive-value checks where appropriate.
- Existing Python services use the helpers without behavior changes.
- A service template pattern doc shows sensor and processor skeletons.
- Tests cover the shared CLI helpers.
- Existing tests and lint pass.
- Service entry point help still works.

## Risks

Main risk: over-abstracting service code before enough real hardware examples exist.

Mitigation:

- Use functions, not inheritance.
- Keep service loops explicit in each service module.
- Only extract code that is already duplicated.
- Preserve current command-line behavior.
