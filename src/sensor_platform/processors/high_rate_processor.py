"""Processor for high-rate ADC batches."""

from __future__ import annotations

import argparse

import paho.mqtt.client as mqtt

from sensor_platform.config import (
    HIGH_RATE_PROCESSOR_RESULTS_TOPIC,
    HIGH_RATE_SENSOR_BATCHES_TOPIC,
)
from sensor_platform.core.cli import add_logging_arguments, add_mqtt_arguments, require_positive_int
from sensor_platform.core.mqtt_client import create_client
from sensor_platform.core.protobuf_helpers import parse_adc_sample_batch, serialize_message
from sensor_platform.core.service_logging import configure_logging
from sensor_platform.generated import sensor_platform_pb2
from sensor_platform.sensors.high_rate_batch import summarize_batch


def build_parser() -> argparse.ArgumentParser:
    """Allow the plot downsampling size to be changed without code edits."""
    parser = argparse.ArgumentParser(description="Process high-rate ADC batches from MQTT.")
    add_mqtt_arguments(parser)
    add_logging_arguments(parser)
    parser.add_argument("--max-downsampled-points", type=int, default=200)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    configure_logging(args.log_level)
    require_positive_int(args.max_downsampled_points, "--max-downsampled-points")

    client = create_client("high-rate-processor")

    def on_connect(
        client: mqtt.Client,
        userdata: object,
        flags: mqtt.ConnectFlags,
        reason_code: mqtt.ReasonCode,
        properties: mqtt.Properties | None,
    ) -> None:
        # The high-rate processor only needs the raw batch topic.
        if reason_code.is_failure:
            print(f"Failed to connect to MQTT broker: {reason_code}")
            return
        client.subscribe(HIGH_RATE_SENSOR_BATCHES_TOPIC)
        print(f"Subscribed to {HIGH_RATE_SENSOR_BATCHES_TOPIC}")

    def on_message(client: mqtt.Client, userdata: object, message: mqtt.MQTTMessage) -> None:
        try:
            # Decode the batch and summarize it before publishing a smaller processed message.
            batch = parse_adc_sample_batch(message.payload)
            summary = summarize_batch(
                list(batch.raw_values),
                reference_voltage=batch.reference_voltage,
                max_downsampled_points=args.max_downsampled_points,
            )
        except ValueError as exc:
            print(f"Skipping invalid high-rate payload: {exc}")
            return

        # The GUI plots downsampled data while the table shows summary statistics.
        processed = sensor_platform_pb2.ProcessedSampleBatch(
            sensor_id=batch.sensor_id,
            start_timestamp_us=batch.start_timestamp_us,
            channel=batch.channel,
            sample_rate_hz=batch.sample_rate_hz,
            sample_count=batch.sample_count,
            min_voltage=summary.min_voltage,
            max_voltage=summary.max_voltage,
            average_voltage=summary.average_voltage,
            rms_voltage=summary.rms_voltage,
            downsampled_voltages=summary.downsampled_voltages,
        )
        client.publish(HIGH_RATE_PROCESSOR_RESULTS_TOPIC, serialize_message(processed))
        print(
            f"sensor={processed.sensor_id} channel={processed.channel} "
            f"samples={processed.sample_count} avg={processed.average_voltage:.3f} V "
            f"min={processed.min_voltage:.3f} V max={processed.max_voltage:.3f} V "
            f"rms={processed.rms_voltage:.3f} V"
        )

    client.on_connect = on_connect
    client.on_message = on_message

    print(
        f"Processing high-rate batches from {HIGH_RATE_SENSOR_BATCHES_TOPIC} and publishing to "
        f"{HIGH_RATE_PROCESSOR_RESULTS_TOPIC}. Press Ctrl+C to stop."
    )
    client.connect(args.mqtt_host, args.mqtt_port)
    try:
        client.loop_forever()
    except KeyboardInterrupt:
        print("Stopping high-rate processor.")
    finally:
        client.disconnect()


if __name__ == "__main__":
    main()
