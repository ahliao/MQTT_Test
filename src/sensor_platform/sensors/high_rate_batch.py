"""Pure functions for generating and summarizing high-rate ADC batches."""

from __future__ import annotations

import math
import random
from dataclasses import dataclass

from sensor_platform.config import ADC_MAX_VALUE, ADC_REFERENCE_VOLTAGE


@dataclass(frozen=True)
class BatchSummary:
    """Small processed representation of a larger raw sample batch."""

    min_voltage: float
    max_voltage: float
    average_voltage: float
    rms_voltage: float
    downsampled_voltages: list[float]


def generate_raw_batch(
    *,
    sample_count: int,
    sample_rate_hz: int,
    batch_index: int,
    adc_max_value: int = ADC_MAX_VALUE,
    noise_fraction: float = 0.02,
) -> list[int]:
    """Generate one synthetic high-rate ADC batch.

    The sensor publishes one protobuf message per batch instead of one MQTT
    message per sample. At 10 kHz, a batch of 500 samples becomes 20 MQTT
    messages per second instead of 10,000 messages per second.
    """
    if sample_count < 1:
        raise ValueError("sample_count must be at least 1")
    if sample_rate_hz < 1:
        raise ValueError("sample_rate_hz must be at least 1")

    base_sample_index = batch_index * sample_count
    raw_values: list[int] = []
    for offset in range(sample_count):
        sample_index = base_sample_index + offset
        timestamp_s = sample_index / sample_rate_hz
        slow_wave = math.sin(2.0 * math.pi * 7.0 * timestamp_s)
        faster_wave = 0.25 * math.sin(2.0 * math.pi * 80.0 * timestamp_s)
        noise = random.uniform(-noise_fraction, noise_fraction)
        normalized = min(max(0.5 + 0.35 * slow_wave + faster_wave + noise, 0.0), 1.0)
        raw_values.append(round(normalized * adc_max_value))
    return raw_values


def raw_values_to_voltages(
    raw_values: list[int],
    *,
    adc_max_value: int = ADC_MAX_VALUE,
    reference_voltage: float = ADC_REFERENCE_VOLTAGE,
) -> list[float]:
    """Convert a batch of raw ADC counts into engineering units."""
    return [(raw_value / adc_max_value) * reference_voltage for raw_value in raw_values]


def summarize_batch(
    raw_values: list[int],
    *,
    reference_voltage: float = ADC_REFERENCE_VOLTAGE,
    adc_max_value: int = ADC_MAX_VALUE,
    max_downsampled_points: int = 200,
) -> BatchSummary:
    """Compute statistics and reduce a large batch to plot-friendly points."""
    if not raw_values:
        raise ValueError("raw_values must not be empty")
    if max_downsampled_points < 1:
        raise ValueError("max_downsampled_points must be at least 1")

    voltages = raw_values_to_voltages(
        raw_values,
        adc_max_value=adc_max_value,
        reference_voltage=reference_voltage,
    )
    average_voltage = sum(voltages) / len(voltages)
    rms_voltage = math.sqrt(sum(voltage * voltage for voltage in voltages) / len(voltages))
    # Downsampling keeps the GUI responsive even when raw batches contain many samples.
    step = max(1, math.ceil(len(voltages) / max_downsampled_points))
    downsampled = voltages[::step]
    return BatchSummary(
        min_voltage=min(voltages),
        max_voltage=max(voltages),
        average_voltage=average_voltage,
        rms_voltage=rms_voltage,
        downsampled_voltages=downsampled,
    )


def batch_time_axis_seconds(*, sample_count: int, sample_rate_hz: int) -> list[float]:
    """Build a time axis for samples that are evenly spaced by sample rate."""
    if sample_count < 1:
        return []
    return [index / sample_rate_hz for index in range(sample_count)]
