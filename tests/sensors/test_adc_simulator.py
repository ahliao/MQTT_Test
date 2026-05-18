"""Tests for the low-rate ADC simulator and voltage conversion."""

from __future__ import annotations

import pytest

from sensor_platform.sensors.adc_simulator import SimulatedAdc, raw_to_voltage
from sensor_platform.config import ADC_MAX_VALUE, ADC_REFERENCE_VOLTAGE


def test_raw_to_voltage_at_zero() -> None:
    assert raw_to_voltage(0) == 0.0


def test_raw_to_voltage_at_max() -> None:
    assert raw_to_voltage(ADC_MAX_VALUE) == ADC_REFERENCE_VOLTAGE


def test_raw_to_voltage_rejects_out_of_range_value() -> None:
    with pytest.raises(ValueError):
        raw_to_voltage(ADC_MAX_VALUE + 1)


def test_simulated_adc_sample_stays_in_expected_range() -> None:
    # The exact simulated value is random, so test the physical bounds instead.
    adc = SimulatedAdc(channel=2)
    sample = adc.read()

    assert sample.channel == 2
    assert 0 <= sample.raw_value <= ADC_MAX_VALUE
    assert 0.0 <= sample.voltage <= ADC_REFERENCE_VOLTAGE
