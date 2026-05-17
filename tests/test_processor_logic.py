from __future__ import annotations

import pytest

from sensor_platform.processor_logic import MovingAverage, classify_voltage


def test_moving_average_uses_available_values() -> None:
    average = MovingAverage(window_size=3)

    assert average.add(1.0) == 1.0
    assert average.add(2.0) == 1.5
    assert average.add(3.0) == 2.0


def test_moving_average_drops_old_values() -> None:
    average = MovingAverage(window_size=2)

    average.add(1.0)
    average.add(2.0)


    assert average.add(5.0) == 3.5


def test_moving_average_rejects_invalid_window_size() -> None:
    with pytest.raises(ValueError):
        MovingAverage(window_size=0)


@pytest.mark.parametrize(
    ("voltage", "state"),
    [
        (0.5, "LOW"),
        (1.5, "NORMAL"),
        (2.8, "HIGH"),
    ],
)
def test_classify_voltage(voltage: float, state: str) -> None:
    assert classify_voltage(voltage) == state
