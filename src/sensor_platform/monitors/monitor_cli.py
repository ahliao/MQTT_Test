"""Terminal monitor for the low-rate sensor and processor streams."""

from __future__ import annotations

import argparse
import os
import threading
import time

import paho.mqtt.client as mqtt

from sensor_platform.config import MQTT_HOST, MQTT_PORT, PROCESSOR_RESULTS_TOPIC, SENSOR_READINGS_TOPIC
from sensor_platform.core.mqtt_client import create_client
from sensor_platform.core.protobuf_helpers import parse_adc_reading, parse_processed_reading
from sensor_platform.monitors.monitor_state import MonitorState


def build_parser() -> argparse.ArgumentParser:
    """Define display and broker options for the CLI monitor."""
    parser = argparse.ArgumentParser(description="Display live sensor and processor MQTT data.")
    parser.add_argument("--mqtt-host", default=MQTT_HOST)
    parser.add_argument("--mqtt-port", type=int, default=MQTT_PORT)
    parser.add_argument("--refresh-seconds", type=float, default=1.0)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    state = MonitorState()
    # MQTT callbacks and terminal rendering run concurrently, so protect shared state.
    lock = threading.Lock()
    client = create_client("monitor")

    def on_connect(
        client: mqtt.Client,
        userdata: object,
        flags: mqtt.ConnectFlags,
        reason_code: mqtt.ReasonCode,
        properties: mqtt.Properties | None,
    ) -> None:
        # Subscribe to both raw and processed topics so one table can show both values.
        if reason_code.is_failure:
            print(f"Failed to connect to MQTT broker: {reason_code}")
            return
        client.subscribe([(SENSOR_READINGS_TOPIC, 0), (PROCESSOR_RESULTS_TOPIC, 0)])

    def on_message(client: mqtt.Client, userdata: object, message: mqtt.MQTTMessage) -> None:
        try:
            # Decode each topic into the matching protobuf type before updating state.
            with lock:
                if message.topic == SENSOR_READINGS_TOPIC:
                    state.update_raw(parse_adc_reading(message.payload))
                elif message.topic == PROCESSOR_RESULTS_TOPIC:
                    state.update_processed(parse_processed_reading(message.payload))
        except ValueError as exc:
            print(f"Skipping invalid payload on {message.topic}: {exc}")

    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(args.mqtt_host, args.mqtt_port)
    # The network loop runs in a background thread while this module redraws the terminal.
    client.loop_start()

    print("Starting monitor. Press Ctrl+C to stop.")
    try:
        while True:
            with lock:
                snapshots = state.snapshots()
            render_table(snapshots)
            time.sleep(args.refresh_seconds)
    except KeyboardInterrupt:
        print("Stopping monitor.")
    finally:
        client.loop_stop()
        client.disconnect()


def render_table(snapshots: list[object]) -> None:
    """Redraw a simple table of the latest known values."""
    os.system("clear")
    print("Sensor Platform Monitor")
    print("MQTT topics: sensor/adc/readings, processor/adc/results")
    print()
    print(
        f"{'Sensor':<14} {'Ch':>2} {'Raw':>5} {'Voltage':>10} "
        f"{'Avg Voltage':>12} {'State':>8} {'Timestamp ms':>14}"
    )
    print("-" * 76)
    if not snapshots:
        print("Waiting for MQTT messages...")
        return
    for item in snapshots:
        raw = "-" if item.raw_value is None else str(item.raw_value)
        voltage = "-" if item.voltage is None else f"{item.voltage:.3f} V"
        average = (
            "-"
            if item.moving_average_voltage is None
            else f"{item.moving_average_voltage:.3f} V"
        )
        state = item.state or "-"
        print(
            f"{item.sensor_id:<14} {item.channel:>2} {raw:>5} {voltage:>10} "
            f"{average:>12} {state:>8} {item.timestamp_ms:>14}"
        )


if __name__ == "__main__":
    main()
