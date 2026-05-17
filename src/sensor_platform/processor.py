from __future__ import annotations

import argparse
from collections import defaultdict

import paho.mqtt.client as mqtt

from sensor_platform.config import MQTT_HOST, MQTT_PORT, PROCESSOR_RESULTS_TOPIC, SENSOR_READINGS_TOPIC
from sensor_platform.generated import sensor_platform_pb2
from sensor_platform.mqtt_client import create_client
from sensor_platform.processor_logic import MovingAverage, classify_voltage
from sensor_platform.protobuf_helpers import parse_adc_reading, serialize_message
from sensor_platform.time_utils import now_ms


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Process ADC readings from MQTT.")
    parser.add_argument("--mqtt-host", default=MQTT_HOST)
    parser.add_argument("--mqtt-port", type=int, default=MQTT_PORT)
    parser.add_argument("--window-size", type=int, default=5)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    averages: defaultdict[tuple[str, int], MovingAverage] = defaultdict(
        lambda: MovingAverage(window_size=args.window_size)
    )
    client = create_client("processor")

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
        client.subscribe(SENSOR_READINGS_TOPIC)
        print(f"Subscribed to {SENSOR_READINGS_TOPIC}")

    def on_message(client: mqtt.Client, userdata: object, message: mqtt.MQTTMessage) -> None:
        try:
            reading = parse_adc_reading(message.payload)
        except ValueError as exc:
            print(f"Skipping invalid sensor payload: {exc}")
            return

        key = (reading.sensor_id, reading.channel)
        average_voltage = averages[key].add(reading.voltage)
        processed = sensor_platform_pb2.ProcessedReading(
            sensor_id=reading.sensor_id,
            timestamp_ms=now_ms(),
            channel=reading.channel,
            voltage=reading.voltage,
            moving_average_voltage=average_voltage,
            state=classify_voltage(average_voltage),
        )
        client.publish(PROCESSOR_RESULTS_TOPIC, serialize_message(processed))
        print(
            f"sensor={processed.sensor_id} channel={processed.channel} "
            f"voltage={processed.voltage:.3f} V avg={processed.moving_average_voltage:.3f} V "
            f"state={processed.state}"
        )

    client.on_connect = on_connect
    client.on_message = on_message

    print(
        f"Processing readings from {SENSOR_READINGS_TOPIC} and publishing to "
        f"{PROCESSOR_RESULTS_TOPIC}. Press Ctrl+C to stop."
    )
    client.connect(args.mqtt_host, args.mqtt_port)
    try:
        client.loop_forever()
    except KeyboardInterrupt:
        print("Stopping processor.")
    finally:
        client.disconnect()


if __name__ == "__main__":
    main()
