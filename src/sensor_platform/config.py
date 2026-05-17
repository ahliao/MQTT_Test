from __future__ import annotations

MQTT_HOST = "localhost"
MQTT_PORT = 1883

SENSOR_READINGS_TOPIC = "sensor/adc/readings"
PROCESSOR_RESULTS_TOPIC = "processor/adc/results"
PLATFORM_STATUS_TOPIC = "platform/status"

DEFAULT_SENSOR_ID = "sim-adc-01"
DEFAULT_CHANNEL = 0
DEFAULT_SAMPLE_RATE_HZ = 2.0

ADC_BITS = 12
ADC_MAX_VALUE = (2**ADC_BITS) - 1
ADC_REFERENCE_VOLTAGE = 3.3
