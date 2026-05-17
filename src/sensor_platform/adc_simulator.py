from __future__ import annotations

import math
import random
import time
from dataclasses import dataclass

from sensor_platform.config import ADC_MAX_VALUE, ADC_REFERENCE_VOLTAGE


@dataclass(frozen=True)
class SimulatedAdcSample:
    channel: int
    raw_value: int
    voltage: float


def raw_to_voltage(
    raw_value: int,
    *,
    adc_max_value: int = ADC_MAX_VALUE,
    reference_voltage: float = ADC_REFERENCE_VOLTAGE,
) -> float:
    """Convert an ADC count into a voltage."""
    if not 0 <= raw_value <= adc_max_value:
        raise ValueError(f"raw_value must be between 0 and {adc_max_value}")
    return (raw_value / adc_max_value) * reference_voltage


class SimulatedAdc:
    """Small ADC simulator that produces a smooth signal with noise."""

    def __init__(
        self,
        *,
        channel: int = 0,
        adc_max_value: int = ADC_MAX_VALUE,
        reference_voltage: float = ADC_REFERENCE_VOLTAGE,
        noise_fraction: float = 0.03,
    ) -> None:
        self.channel = channel
        self.adc_max_value = adc_max_value
        self.reference_voltage = reference_voltage
        self.noise_fraction = noise_fraction
        self._started_at = time.monotonic()

    def read(self) -> SimulatedAdcSample:
        elapsed = time.monotonic() - self._started_at
        wave = (math.sin(elapsed) + 1.0) / 2.0
        noise = random.uniform(-self.noise_fraction, self.noise_fraction)
        normalized = min(max(wave + noise, 0.0), 1.0)
        raw_value = round(normalized * self.adc_max_value)
        voltage = raw_to_voltage(
            raw_value,
            adc_max_value=self.adc_max_value,
            reference_voltage=self.reference_voltage,
        )
        return SimulatedAdcSample(
            channel=self.channel,
            raw_value=raw_value,
            voltage=voltage,
        )
