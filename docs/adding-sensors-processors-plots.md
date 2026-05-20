# Adding Sensors, Processors, and GUI Plots

## Goal

This document explains how to extend the project with a new sensor, a new processor client, and a new GUI display or plot.

The current project has two examples:

- Low-rate ADC readings: one sample per MQTT message
- High-rate ADC batches: many samples per MQTT message

Use those as patterns when adding new data streams.

## Current Data Flow

The project uses this general shape:

```text
Sensor service
    |
    | MQTT topic with protobuf payload
    v
Processor service
    |
    | MQTT topic with processed protobuf payload
    v
Monitor GUI
```

Each stream needs these design decisions:

- What data does the sensor produce?
- What MQTT topic carries raw data?
- What protobuf message describes raw data?
- What does the processor compute?
- What MQTT topic carries processed data?
- What protobuf message describes processed data?
- How should the GUI display it?

## Step 1: Define the Sensor Data

Start by writing down what one logical measurement means.

Example new sensor: temperature sensor.

Possible raw data:

```text
sensor_id
timestamp_ms
temperature_c
```

Possible processed data:

```text
sensor_id
timestamp_ms
temperature_c
moving_average_c
state
```

For a high-rate or buffered sensor, decide whether one MQTT message should contain many samples.

Use one sample per message when:

- the sample rate is low
- every sample is meaningful on its own
- the message rate is easy for MQTT and the GUI to handle

Use batching when:

- the sample rate is high
- one message per sample would create too many MQTT messages
- the processor can operate on chunks of data

## Step 2: Add MQTT Topics

Add topic constants in `src/sensor_platform/config.py`.

Example:

```python
TEMPERATURE_READINGS_TOPIC = "sensor/temperature/readings"
TEMPERATURE_RESULTS_TOPIC = "processor/temperature/results"
```

Keep topic names specific and readable.

Recommended topic pattern:

```text
sensor/<sensor-kind>/<data-kind>
processor/<sensor-kind>/<result-kind>
```

Examples:

```text
sensor/temperature/readings
processor/temperature/results
sensor/vibration/batches
processor/vibration/spectrum
```

See `docs/message-design-guidelines.md` for detailed topic naming rules.

## Step 3: Add Protobuf Messages

Edit `proto/sensor_platform.proto`.

Example:

```proto
message TemperatureReading {
  string sensor_id = 1;
  int64 timestamp_ms = 2;
  double temperature_c = 3;
}

message ProcessedTemperatureReading {
  string sensor_id = 1;
  int64 timestamp_ms = 2;
  double temperature_c = 3;
  double moving_average_c = 4;
  string state = 5;
}
```

Important protobuf rules:

- Do not reuse field numbers after a message is in use.
- Add new fields with new numbers.
- Keep message names clear.
- Keep units in field names when useful, such as `temperature_c`, `voltage`, or `timestamp_ms`.
- Use low-rate sample messages for slow streams and batch messages for high-rate streams.

See `docs/message-design-guidelines.md` before adding or changing protobuf messages.

After changing the schema, regenerate Python code:

```bash
uv run generate-protobuf
```

## Step 4: Add Protobuf Helper Functions

Edit `src/sensor_platform/core/protobuf_helpers.py`.

Add parser helpers for the new message types.

Example:

```python
def parse_temperature_reading(payload: bytes) -> sensor_platform_pb2.TemperatureReading:
    reading = sensor_platform_pb2.TemperatureReading()
    _parse_into(reading, payload)
    return reading


def parse_processed_temperature_reading(
    payload: bytes,
) -> sensor_platform_pb2.ProcessedTemperatureReading:
    reading = sensor_platform_pb2.ProcessedTemperatureReading()
    _parse_into(reading, payload)
    return reading
```

This keeps MQTT byte parsing out of the sensor, processor, and GUI code.

## Step 5: Add the Sensor Service

Create a new module under `src/sensor_platform/sensors/`.

Example:

```text
src/sensor_platform/sensors/temperature_sensor.py
```

The sensor service should:

- parse command-line options
- use shared CLI helpers from `src/sensor_platform/core/cli.py`
- connect to MQTT
- read or simulate sensor data
- create a protobuf message
- serialize it
- publish it to the raw sensor topic

Skeleton:

```python
from sensor_platform.config import MQTT_HOST, MQTT_PORT, TEMPERATURE_READINGS_TOPIC
from sensor_platform.core.cli import add_mqtt_arguments, add_logging_arguments
from sensor_platform.generated import sensor_platform_pb2
from sensor_platform.core.mqtt_client import create_client
from sensor_platform.core.protobuf_helpers import serialize_message
from sensor_platform.core.time_utils import now_ms


def main() -> None:
    client = create_client("temperature-sensor")
    client.connect(MQTT_HOST, MQTT_PORT)
    client.loop_start()

    reading = sensor_platform_pb2.TemperatureReading(
        sensor_id="temp-01",
        timestamp_ms=now_ms(),
        temperature_c=25.0,
    )
    client.publish(TEMPERATURE_READINGS_TOPIC, serialize_message(reading))
```

See `docs/service-template-pattern.md` for the recommended full sensor service shape.

Add a script entry in `pyproject.toml`:

```toml
sensor-platform-temperature-sensor = "sensor_platform.sensors.temperature_sensor:main"
```

Then run it with:

```bash
uv run sensor-platform-temperature-sensor
```

## Step 6: Add Pure Processing Logic

If possible, put the math in a separate pure-Python module before writing the MQTT processor.

Example:

```text
src/sensor_platform/processors/temperature_logic.py
```

This makes the logic easy to test without an MQTT broker.

Example:

```python
def classify_temperature(temperature_c: float) -> str:
    if temperature_c < 10.0:
        return "COLD"
    if temperature_c > 35.0:
        return "HOT"
    return "NORMAL"
```

Add tests under `tests/`.

Example:

```text
tests/test_temperature_logic.py
```

## Step 7: Add the Processor Service

Create a new processor module.

Example:

```text
src/sensor_platform/processors/temperature_processor.py
```

The processor should:

- subscribe to the raw sensor topic
- parse the raw protobuf message
- compute processed values
- publish a processed protobuf message

Skeleton:

```python
import paho.mqtt.client as mqtt

from sensor_platform.config import TEMPERATURE_READINGS_TOPIC, TEMPERATURE_RESULTS_TOPIC
from sensor_platform.generated import sensor_platform_pb2
from sensor_platform.core.mqtt_client import create_client
from sensor_platform.core.protobuf_helpers import (
    parse_temperature_reading,
    serialize_message,
)


def main() -> None:
    client = create_client("temperature-processor")

    def on_connect(
        client: mqtt.Client,
        userdata: object,
        flags: mqtt.ConnectFlags,
        reason_code: mqtt.ReasonCode,
        properties: mqtt.Properties | None,
    ) -> None:
        client.subscribe(TEMPERATURE_READINGS_TOPIC)

    def on_message(client: mqtt.Client, userdata: object, message: mqtt.MQTTMessage) -> None:
        reading = parse_temperature_reading(message.payload)
        processed = sensor_platform_pb2.ProcessedTemperatureReading(
            sensor_id=reading.sensor_id,
            timestamp_ms=reading.timestamp_ms,
            temperature_c=reading.temperature_c,
            moving_average_c=reading.temperature_c,
            state="NORMAL",
        )
        client.publish(TEMPERATURE_RESULTS_TOPIC, serialize_message(processed))

    client.on_connect = on_connect
    client.on_message = on_message
    client.connect("localhost", 1883)
    client.loop_forever()
```

Add a script entry in `pyproject.toml`:

```toml
sensor-platform-temperature-processor = "sensor_platform.processors.temperature_processor:main"
```

## Step 8: Add GUI Support

The project now has a shared stream registry that describes known MQTT topics and protobuf parsers.

The central file is:

```text
src/sensor_platform/streams.py
```

That file defines:

- stable stream names
- display names
- MQTT topics
- protobuf parser functions
- stream kind metadata
- whether a stream is monitored by default

Example from the current project:

```python
StreamConfig(
    name=HIGH_RATE_PROCESSED_ADC_STREAM,
    display_name="High-rate processed ADC batches",
    topic=HIGH_RATE_PROCESSOR_RESULTS_TOPIC,
    parser=parse_processed_sample_batch,
    kind=StreamKind.HIGH_RATE_PROCESSED_BATCH,
)
```

To add a new stream, first add a new config entry to `STREAMS`.

Example:

```python
TEMPERATURE_PROCESSED_STREAM = "temperature_processed"

STREAMS = (
    ...,
    StreamConfig(
        name=TEMPERATURE_PROCESSED_STREAM,
        display_name="Processed temperature readings",
        topic=TEMPERATURE_RESULTS_TOPIC,
        parser=parse_processed_temperature_reading,
        kind=StreamKind.LOW_RATE_PROCESSED,
    ),
)
```

After that, the GUI can subscribe to the topic and parse the protobuf payload through the shared registry. Streams with `default_visible=False` stay registered but are not monitored by the GUI by default.

The GUI display layer is still partly hard-coded. It explicitly knows how to display:

- low-rate ADC readings
- low-rate processed readings
- high-rate processed batches
- the low-rate plot
- the high-rate plot

To display a new configured stream today, update:

- `src/sensor_platform/gui/monitor_qt.py`
- possibly `src/sensor_platform/gui/plot_history.py`

Current manual steps:

1. Add the stream config in `streams.py`.
2. Add a handler branch in `MonitorWindow._handle_decoded_message()`.
3. Add a handler method in `MonitorWindow`.
4. Add a table or plot widget if the existing widgets do not fit.
5. Update that widget when messages arrive.

The important improvement is that MQTT subscription and protobuf parsing no longer need to be edited in `qt_mqtt_worker.py` for every new stream.

## Current Stream Registry Design

The shared registry describes each stream:

- MQTT topic
- protobuf parser
- display name
- stream kind
- default visibility

Current registry object:

```python
@dataclass(frozen=True)
class StreamConfig:
    name: str
    display_name: str
    topic: str
    parser: Callable[[bytes], object]
    kind: StreamKind
    default_visible: bool = True
```

The MQTT worker loops over GUI-visible stream configs instead of hard-coding topics.

List registered streams with:

```bash
uv run sensor-platform-list-streams
```

## Remaining GUI Expansion Plan

The next improvement is to make table and plot widgets configuration-driven too.

The future config should add:

- table columns
- plot series
- update strategy
- display panel type

Conceptual future config:

```python
@dataclass(frozen=True)
class TableColumnConfig:
    title: str
    getter: Callable[[object], str]


@dataclass(frozen=True)
class PlotSeriesConfig:
    label: str
    color: str
    y_getter: Callable[[object], float]
```

## Suggested Refactor Plan

### Phase 1: Centralize Stream Definitions

Status: implemented.

Create `streams.py` and move shared topic/parser/display definitions into it.

First targets:

- low-rate raw ADC stream
- low-rate processed ADC stream
- high-rate raw ADC batch stream
- high-rate processed ADC batch stream

The goal is not to make everything generic immediately. The goal is to gather stream metadata in one place.

### Phase 2: Make MQTT Worker Subscribe From Config

Status: implemented.

Change `MqttWorker` so it receives a list of stream configs.

Instead of hard-coding:

```python
client.subscribe([
    (SENSOR_READINGS_TOPIC, 0),
    (PROCESSOR_RESULTS_TOPIC, 0),
    (HIGH_RATE_PROCESSOR_RESULTS_TOPIC, 0),
])
```

It would do:

```python
client.subscribe([(stream.topic, 0) for stream in streams])
```

When a message arrives, it finds the stream config by topic, parses the payload, and emits a generic decoded-message signal.

### Phase 3: Add Generic Table Panels

Status: not implemented yet.

Create a reusable table widget that is configured by column definitions.

Example column config:

```python
TableColumnConfig(
    title="Average",
    getter=lambda message: f"{message.average_voltage:.3f} V",
)
```

The table widget would not know whether the data is ADC, temperature, vibration, or something else.

### Phase 4: Add Generic Plot Panels

Status: not implemented yet.

Create reusable plot panel types:

- point-stream plot for low-rate samples
- rolling-window plot for high-rate batches

The plot config would define how to extract x/y values from messages.

For low-rate processed temperature:

```python
y_getter=lambda message: message.temperature_c
```

For high-rate batch voltage:

```python
y_values_getter=lambda message: list(message.downsampled_voltages)
```

### Phase 5: Add Sensor Plugin-Like Modules

Status: not implemented yet.

Once the GUI config is centralized, each sensor type can have one small module that exports its display config.

Example:

```text
src/sensor_platform/sensors/temperature.py
```

That module could contain:

- topic constants
- parser helpers
- table column config
- plot config
- optional processor logic

This would make new sensors feel more like adding a plugin.

## What Was Implemented First

The first refactor intentionally stopped before generic widgets:

1. Added `gui/config.py`.
2. Moved high-rate and low-rate topic/parser metadata into config objects.
3. Made `MqttWorker` subscribe based on that config.
4. Made `MqttWorker` emit a generic decoded-message signal.
5. Kept the current table and plot widgets mostly as-is.
6. Added `streams.py` as the shared stream registry.
7. Added `sensor-platform-list-streams` to inspect registered streams.

This gives a cleaner extension point without rewriting the whole GUI at once.

## Checklist for Adding a New Sensor Today

Use this checklist before the GUI refactor exists:

1. Add MQTT topic constants in `config.py`.
2. Add protobuf messages in `proto/sensor_platform.proto`.
3. Run `uv run generate-protobuf`.
4. Add protobuf parser helpers in `core/protobuf_helpers.py`.
5. Add the sensor service module.
6. Add pure processing logic and tests.
7. Add the processor service module.
8. Add script entries in `pyproject.toml`.
9. Use the service template pattern from `docs/service-template-pattern.md`.
10. Add the new stream to `streams.py`.
11. Update `gui/monitor_qt.py` to display the new stream.
12. Check the message design rules in `docs/message-design-guidelines.md`.
13. Update docs and README commands.
14. Run `uv run pytest` and `uv run ruff check .`.

## Design Advice

- Keep sensor hardware access separate from MQTT publishing.
- Keep processing math separate from MQTT callbacks.
- Keep protobuf parsing in helper functions.
- Use one MQTT topic per clear message type.
- Prefer batching for high-rate data.
- Avoid putting every raw high-rate sample into a GUI table.
- Add tests for pure logic before testing MQTT integration.
