# Message Design Guidelines

## Goal

Define consistent MQTT topic and protobuf message patterns for new sensors, processors, monitors, and future native Rust or C++ publishers.

Use this guide before changing:

```text
proto/sensor_platform.proto
src/sensor_platform/config.py
src/sensor_platform/streams.py
```

## Design Principles

- Treat MQTT topics and protobuf messages as public service contracts.
- Prefer explicit names over short names.
- Include units in field names when the unit is not obvious.
- Keep hardware access details out of protobuf messages unless consumers need them.
- Use one MQTT topic for one clear protobuf message type.
- Use batched messages for high-rate streams instead of one MQTT message per sample.
- Add fields safely; do not reuse field numbers.

## Topic Naming

Use readable topics that describe the publisher side and the data kind.

Recommended topic shapes:

```text
sensor/<sensor-kind>/<data-kind>
processor/<sensor-kind>/<result-kind>
platform/<event-kind>
```

Examples:

```text
sensor/adc/readings
processor/adc/results
sensor/adc/high-rate/batches
processor/adc/high-rate/results
platform/status
```

For new sensors:

```text
sensor/temperature/readings
processor/temperature/results
sensor/gps/fixes
processor/gps/results
sensor/vibration/batches
processor/vibration/spectrum
```

Guidelines:

- Use lowercase topic segments.
- Use hyphens for multi-word topic segments, such as `high-rate`.
- Keep raw sensor topics under `sensor/...`.
- Keep derived data under `processor/...`.
- Keep service health and operational events under `platform/...`.
- Avoid putting sensor IDs in the topic unless there is a measured routing need. Prefer `sensor_id` inside the protobuf payload.

## Protobuf Message Naming

Use `PascalCase` message names.

Recommended patterns:

| Message Role | Name Pattern | Example |
| --- | --- | --- |
| One low-rate raw sample | `<SensorKind>Reading` | `TemperatureReading` |
| One processed low-rate sample | `Processed<SensorKind>Reading` | `ProcessedTemperatureReading` |
| Raw high-rate batch | `<SensorKind>SampleBatch` | `VibrationSampleBatch` |
| Processed high-rate batch | `Processed<SensorKind>SampleBatch` | `ProcessedVibrationSampleBatch` |
| Device or service status | `ServiceStatus` or `<DeviceKind>Status` | `ServiceStatus` |
| Operational error event | `<SourceKind>Error` | `SensorError` |

Use specific names when generic names would become confusing. For example, prefer `GpsFix` over `GpsReading` if the message represents a parsed GPS fix.

## Field Naming

Use `snake_case` field names.

Recommended common fields:

```proto
string sensor_id = 1;
int64 timestamp_ms = 2;
uint32 channel = 3;
```

For batch messages:

```proto
string sensor_id = 1;
int64 start_timestamp_us = 2;
uint32 channel = 3;
uint32 sample_rate_hz = 4;
uint32 sample_count = 5;
```

Field naming rules:

- Include units in names: `temperature_c`, `timestamp_ms`, `sample_rate_hz`, `pressure_kpa`.
- Use `timestamp_ms` for low-rate event timestamps.
- Use `start_timestamp_us` for high-rate batches where sample spacing matters.
- Use `sample_count` when a message carries repeated samples.
- Use `raw_value` or `raw_values` for ADC counts or device-native units.
- Use measured units for converted values, such as `voltage`, `temperature_c`, or `acceleration_mps2`.

Avoid ambiguous names:

```proto
double value = 3;        // Avoid: unit and meaning are unclear.
int64 timestamp = 4;     // Avoid: unit is unclear.
double temperature = 5;  // Avoid unless the unit is documented elsewhere.
```

Prefer:

```proto
double temperature_c = 3;
int64 timestamp_ms = 4;
```

## Field Number Rules

Field numbers are part of the binary contract.

Rules:

- Do not change a field number once a message is in use.
- Do not reuse a removed field number for a different meaning.
- Add new fields with new numbers.
- Keep low field numbers for common fields, but do not renumber existing fields to make them prettier.
- Prefer appending fields over restructuring an existing message.

Safe change example:

```proto
message TemperatureReading {
  string sensor_id = 1;
  int64 timestamp_ms = 2;
  double temperature_c = 3;
  double humidity_percent = 4;  // New field with a new number.
}
```

Unsafe change example:

```proto
message TemperatureReading {
  string sensor_id = 1;
  double humidity_percent = 2;  // Unsafe: field 2 used to be timestamp_ms.
  double temperature_c = 3;
}
```

If a field is removed from a long-lived message, reserve its number and name:

```proto
message TemperatureReading {
  reserved 4;
  reserved "humidity_percent";

  string sensor_id = 1;
  int64 timestamp_ms = 2;
  double temperature_c = 3;
}
```

## Low-Rate Sample Pattern

Use one MQTT message per logical measurement when the rate is low and every sample is independently meaningful.

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

Topic pair:

```text
sensor/temperature/readings
processor/temperature/results
```

Use this pattern for:

- temperature
- pressure
- humidity
- slow ADC readings
- GPS fixes
- device status readings

## High-Rate Batch Pattern

Use one MQTT message for many samples when sample rate is high.

Example:

```proto
message VibrationSampleBatch {
  string sensor_id = 1;
  int64 start_timestamp_us = 2;
  uint32 channel = 3;
  uint32 sample_rate_hz = 4;
  uint32 sample_count = 5;
  repeated double acceleration_g = 6;
}

message ProcessedVibrationSampleBatch {
  string sensor_id = 1;
  int64 start_timestamp_us = 2;
  uint32 channel = 3;
  uint32 sample_rate_hz = 4;
  uint32 sample_count = 5;
  double rms_g = 6;
  double peak_g = 7;
  repeated double downsampled_acceleration_g = 8;
}
```

Topic pair:

```text
sensor/vibration/batches
processor/vibration/results
```

Use this pattern for:

- high-rate ADC
- vibration
- audio-like waveforms
- buffered DAQ reads
- native Rust or C++ publishers that acquire blocks of samples

High-rate guidance:

- Include `sample_rate_hz` and `sample_count`.
- Use `start_timestamp_us` for the first sample in the batch.
- Consumers can derive sample times from `start_timestamp_us`, `sample_rate_hz`, and sample index.
- Do not publish one MQTT message per high-rate sample.
- Downsample before plotting large batches in the GUI.

## Status Message Pattern

Use status messages for service health, startup, shutdown, warnings, and future GUI health panels.

Current message:

```proto
message ServiceStatus {
  string service_name = 1;
  int64 timestamp_ms = 2;
  string status = 3;
  string message = 4;
}
```

Recommended topic:

```text
platform/status
```

Recommended `status` values:

```text
STARTING
RUNNING
WARNING
ERROR
STOPPING
STOPPED
```

Keep `message` human-readable. If consumers need structured error codes later, add a new field instead of overloading `message`.

## Error Message Pattern

For now, most services log errors locally and skip invalid payloads. Add explicit protobuf error events only when another service or monitor needs to react to them.

If needed later:

```proto
message SensorError {
  string sensor_id = 1;
  int64 timestamp_ms = 2;
  string error_code = 3;
  string message = 4;
  bool recoverable = 5;
}
```

Recommended topic:

```text
platform/errors
```

Guidelines:

- Use logs for local debugging.
- Use protobuf error events for cross-service behavior.
- Keep error messages human-readable.
- Add machine-readable fields only when there is a consumer for them.

## Adding a New Message Type

Checklist:

1. Choose the topic pair first.
2. Choose whether the raw data is low-rate samples or high-rate batches.
3. Name the protobuf messages using the patterns above.
4. Add fields with explicit units.
5. Assign new field numbers and do not reuse old ones.
6. Add parser helpers in `src/sensor_platform/core/protobuf_helpers.py`.
7. Register the stream in `src/sensor_platform/streams.py`.
8. Run `uv run generate-protobuf`.
9. Add tests for parsing, processing logic, and registry metadata.

## Native Publisher Considerations

Rust and C++ publishers should use the same `.proto` file and publish to the same MQTT topics as Python services.

Rules for native publishers:

- Generate language-specific protobuf code from `proto/sensor_platform.proto`.
- Do not hand-roll binary payloads.
- Use the exact topic names from the Python project documentation.
- Match timestamp units and field units exactly.
- Prefer high-rate batch messages for native high-speed acquisition.

This keeps Python processors and GUI monitors compatible with native sensor services.
