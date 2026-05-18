"""High-rate sensor publisher that batches many ADC samples per MQTT message."""

from __future__ import annotations

import argparse
import time

from sensor_platform.config import (
    ADC_REFERENCE_VOLTAGE,
    DEFAULT_CHANNEL,
    DEFAULT_HIGH_RATE_BATCH_SIZE,
    DEFAULT_HIGH_RATE_SAMPLE_RATE_HZ,
    DEFAULT_SENSOR_ID,
    HIGH_RATE_SENSOR_BATCHES_TOPIC,
    MQTT_HOST,
    MQTT_PORT,
)
from sensor_platform.core.mqtt_client import create_client
from sensor_platform.core.protobuf_helpers import serialize_message
from sensor_platform.core.time_utils import now_us
from sensor_platform.generated import sensor_platform_pb2
from sensor_platform.sensors.high_rate_batch import generate_raw_batch


def build_parser() -> argparse.ArgumentParser:
    """Expose sample rate and batch size so the batching tradeoff is easy to explore."""
    parser = argparse.ArgumentParser(
        description="Publish high-rate simulated ADC samples as protobuf batches."
    )
    parser.add_argument("--mqtt-host", default=MQTT_HOST)
    parser.add_argument("--mqtt-port", type=int, default=MQTT_PORT)
    parser.add_argument("--sensor-id", default=f"{DEFAULT_SENSOR_ID}-high-rate")
    parser.add_argument("--channel", type=int, default=DEFAULT_CHANNEL)
    parser.add_argument("--sample-rate-hz", type=int, default=DEFAULT_HIGH_RATE_SAMPLE_RATE_HZ)
    parser.add_argument("--batch-size", type=int, default=DEFAULT_HIGH_RATE_BATCH_SIZE)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if args.sample_rate_hz <= 0:
        raise SystemExit("--sample-rate-hz must be greater than 0")
    if args.batch_size <= 0:
        raise SystemExit("--batch-size must be greater than 0")

    client = create_client("high-rate-sensor")
    client.connect(args.mqtt_host, args.mqtt_port)
    client.loop_start()

    # A 10 kHz stream with 500 samples per batch publishes 20 MQTT messages/second.
    batch_interval_s = args.batch_size / args.sample_rate_hz
    batch_index = 0
    print(
        f"Publishing {args.sample_rate_hz} Hz ADC data as batches of {args.batch_size} "
        f"samples to {HIGH_RATE_SENSOR_BATCHES_TOPIC}. Press Ctrl+C to stop."
    )

    try:
        while True:
            started_at = time.monotonic()
            # The generated raw values represent samples inside one contiguous ADC buffer.
            raw_values = generate_raw_batch(
                sample_count=args.batch_size,
                sample_rate_hz=args.sample_rate_hz,
                batch_index=batch_index,
            )
            # One protobuf message carries metadata plus the repeated raw sample array.
            batch = sensor_platform_pb2.AdcSampleBatch(
                sensor_id=args.sensor_id,
                start_timestamp_us=now_us(),
                channel=args.channel,
                sample_rate_hz=args.sample_rate_hz,
                sample_count=len(raw_values),
                reference_voltage=ADC_REFERENCE_VOLTAGE,
                raw_values=raw_values,
            )
            client.publish(HIGH_RATE_SENSOR_BATCHES_TOPIC, serialize_message(batch))
            print(
                f"batch={batch_index} samples={batch.sample_count} "
                f"rate={batch.sample_rate_hz} Hz first_raw={batch.raw_values[0]}"
            )
            batch_index += 1

            elapsed_s = time.monotonic() - started_at
            # Sleep for the remaining batch period to approximate the requested sample rate.
            time.sleep(max(0.0, batch_interval_s - elapsed_s))
    except KeyboardInterrupt:
        print("Stopping high-rate sensor publisher.")
    finally:
        client.loop_stop()
        client.disconnect()


if __name__ == "__main__":
    main()
