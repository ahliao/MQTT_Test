"""Shared configuration constants used by the demo services."""

from __future__ import annotations

# Default broker address for local development on WSL Ubuntu or embedded Linux.
MQTT_HOST = "localhost"
MQTT_PORT = 1883

# MQTT topics are the public message contract between independent services.
SENSOR_READINGS_TOPIC = "sensor/adc/readings"
PROCESSOR_RESULTS_TOPIC = "processor/adc/results"
HIGH_RATE_SENSOR_BATCHES_TOPIC = "sensor/adc/high-rate/batches"
HIGH_RATE_PROCESSOR_RESULTS_TOPIC = "processor/adc/high-rate/results"
PLATFORM_STATUS_TOPIC = "platform/status"

# Low-rate sensor defaults keep the first demo easy to watch in a terminal.
DEFAULT_SENSOR_ID = "sim-adc-01"
DEFAULT_CHANNEL = 0
DEFAULT_SAMPLE_RATE_HZ = 2.0

# High-rate defaults demonstrate batching: 10 kHz / 500 samples = 20 MQTT messages/sec.
DEFAULT_HIGH_RATE_SAMPLE_RATE_HZ = 10_000
DEFAULT_HIGH_RATE_BATCH_SIZE = 500

# ADC constants define a typical 12-bit, 3.3 V converter.
ADC_BITS = 12
ADC_MAX_VALUE = (2**ADC_BITS) - 1
ADC_REFERENCE_VOLTAGE = 3.3
