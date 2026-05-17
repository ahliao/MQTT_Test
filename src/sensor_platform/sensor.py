from __future__ import annotations

import argparse
import time

from sensor_platform.adc_simulator import SimulatedAdc
from sensor_platform.config import (
    DEFAULT_CHANNEL,
    DEFAULT_SAMPLE_RATE_HZ,
    DEFAULT_SENSOR_ID,
    MQTT_HOST,
    MQTT_PORT,
    SENSOR_READINGS_TOPIC,
)
from sensor_platform.generated import sensor_platform_pb2
from sensor_platform.mqtt_client import create_client
from sensor_platform.protobuf_helpers import serialize_message
from sensor_platform.time_utils import now_ms


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Publish simulated ADC readings over MQTT.")
    parser.add_argument("--mqtt-host", default=MQTT_HOST)
    parser.add_argument("--mqtt-port", type=int, default=MQTT_PORT)
    parser.add_argument("--sensor-id", default=DEFAULT_SENSOR_ID)
    parser.add_argument("--channel", type=int, default=DEFAULT_CHANNEL)
    parser.add_argument("--sample-rate-hz", type=float, default=DEFAULT_SAMPLE_RATE_HZ)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if args.sample_rate_hz <= 0:
        raise SystemExit("--sample-rate-hz must be greater than 0")

    adc = SimulatedAdc(channel=args.channel)
    client = create_client("sensor")
    client.connect(args.mqtt_host, args.mqtt_port)
    client.loop_start()

    delay_s = 1.0 / args.sample_rate_hz
    print(
        f"Publishing simulated ADC readings to {SENSOR_READINGS_TOPIC} "
        f"via {args.mqtt_host}:{args.mqtt_port}. Press Ctrl+C to stop."
    )

    try:
        while True:
            sample = adc.read()
            reading = sensor_platform_pb2.AdcReading(
                sensor_id=args.sensor_id,
                timestamp_ms=now_ms(),
                channel=sample.channel,
                raw_value=sample.raw_value,
                voltage=sample.voltage,
            )
            client.publish(SENSOR_READINGS_TOPIC, serialize_message(reading))
            print(
                f"sensor={reading.sensor_id} channel={reading.channel} "
                f"raw={reading.raw_value} voltage={reading.voltage:.3f} V"
            )
            time.sleep(delay_s)
    except KeyboardInterrupt:
        print("Stopping sensor publisher.")
    finally:
        client.loop_stop()
        client.disconnect()


if __name__ == "__main__":
    main()
