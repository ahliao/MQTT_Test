# Service Template Pattern

## Goal

Use a consistent shape for Python sensor and processor services while keeping each service easy to read.

This project intentionally uses small helpers instead of a large service framework.

## Shared Helpers

Common command-line helpers live in:

```text
src/sensor_platform/core/cli.py
```

Use these helpers when adding a Python service:

- `add_mqtt_arguments(parser)`: adds `--mqtt-host` and `--mqtt-port`.
- `add_sensor_identity_arguments(parser)`: adds `--sensor-id` and `--channel`.
- `add_logging_arguments(parser)`: adds `--log-level`.
- `require_positive_float(value, option_name)`: validates positive float options.
- `require_positive_int(value, option_name)`: validates positive integer options.

Logging setup lives in:

```text
src/sensor_platform/core/service_logging.py
```

Use `configure_logging(args.log_level)` after parsing arguments.

## Sensor Service Shape

Use this structure for low-rate sensor publishers:

```python
from __future__ import annotations

import argparse
import time

from sensor_platform.config import TEMPERATURE_READINGS_TOPIC
from sensor_platform.core.cli import (
    add_logging_arguments,
    add_mqtt_arguments,
    add_sensor_identity_arguments,
    require_positive_float,
)
from sensor_platform.core.mqtt_client import create_client
from sensor_platform.core.protobuf_helpers import serialize_message
from sensor_platform.core.service_logging import configure_logging
from sensor_platform.core.time_utils import now_ms
from sensor_platform.generated import sensor_platform_pb2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Publish temperature readings over MQTT.")
    add_mqtt_arguments(parser)
    add_sensor_identity_arguments(parser)
    add_logging_arguments(parser)
    parser.add_argument("--sample-rate-hz", type=float, default=1.0)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    configure_logging(args.log_level)
    require_positive_float(args.sample_rate_hz, "--sample-rate-hz")

    client = create_client("temperature-sensor")
    client.connect(args.mqtt_host, args.mqtt_port)
    client.loop_start()

    delay_s = 1.0 / args.sample_rate_hz
    try:
        while True:
            reading = sensor_platform_pb2.TemperatureReading(
                sensor_id=args.sensor_id,
                timestamp_ms=now_ms(),
                temperature_c=25.0,
            )
            client.publish(TEMPERATURE_READINGS_TOPIC, serialize_message(reading))
            time.sleep(delay_s)
    except KeyboardInterrupt:
        print("Stopping temperature sensor.")
    finally:
        client.loop_stop()
        client.disconnect()
```

Keep hardware access behind a small object or function when possible. That makes it easier to replace real hardware with a simulator or replay source in tests.

## Processor Service Shape

Use this structure for processors:

```python
from __future__ import annotations

import argparse

import paho.mqtt.client as mqtt

from sensor_platform.config import TEMPERATURE_READINGS_TOPIC, TEMPERATURE_RESULTS_TOPIC
from sensor_platform.core.cli import add_logging_arguments, add_mqtt_arguments, require_positive_int
from sensor_platform.core.mqtt_client import create_client
from sensor_platform.core.protobuf_helpers import parse_temperature_reading, serialize_message
from sensor_platform.core.service_logging import configure_logging
from sensor_platform.core.time_utils import now_ms
from sensor_platform.generated import sensor_platform_pb2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Process temperature readings from MQTT.")
    add_mqtt_arguments(parser)
    add_logging_arguments(parser)
    parser.add_argument("--window-size", type=int, default=5)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    configure_logging(args.log_level)
    require_positive_int(args.window_size, "--window-size")

    client = create_client("temperature-processor")

    def on_connect(
        client: mqtt.Client,
        userdata: object,
        flags: mqtt.ConnectFlags,
        reason_code: mqtt.ReasonCode,
        properties: mqtt.Properties | None,
    ) -> None:
        if reason_code.is_failure:
            print(f"Failed to connect to MQTT broker: {reason_code}")
            return
        client.subscribe(TEMPERATURE_READINGS_TOPIC)

    def on_message(client: mqtt.Client, userdata: object, message: mqtt.MQTTMessage) -> None:
        try:
            reading = parse_temperature_reading(message.payload)
        except ValueError as exc:
            print(f"Skipping invalid temperature payload: {exc}")
            return

        processed = sensor_platform_pb2.ProcessedTemperatureReading(
            sensor_id=reading.sensor_id,
            timestamp_ms=now_ms(),
            temperature_c=reading.temperature_c,
            moving_average_c=reading.temperature_c,
            state="NORMAL",
        )
        client.publish(TEMPERATURE_RESULTS_TOPIC, serialize_message(processed))

    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(args.mqtt_host, args.mqtt_port)
    try:
        client.loop_forever()
    except KeyboardInterrupt:
        print("Stopping temperature processor.")
    finally:
        client.disconnect()
```

Keep processor math in a separate module when it has real logic. Test that pure logic without a running MQTT broker.

## Checklist

When adding a Python service:

1. Add shared MQTT options with `add_mqtt_arguments(parser)`.
2. Add shared logging with `add_logging_arguments(parser)` and `configure_logging(args.log_level)`.
3. Add sensor identity options with `add_sensor_identity_arguments(parser)` for sensor publishers.
4. Validate numeric options with `require_positive_float()` or `require_positive_int()`.
5. Keep protobuf parsing in `core/protobuf_helpers.py`.
6. Register new MQTT/protobuf streams in `src/sensor_platform/streams.py`.
7. Put reusable processing logic in a testable module.
8. Add focused tests before adding GUI display code.
