"""Pure processing logic used by the MQTT processor service."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field


def classify_voltage(voltage: float) -> str:
    """Classify a 0-3.3 V sensor signal into a simple state."""
    if voltage < 1.0:
        return "LOW"
    if voltage > 2.3:
        return "HIGH"
    return "NORMAL"


@dataclass
class MovingAverage:
    """Fixed-size moving average for one stream of voltage values."""

    window_size: int = 5
    _values: deque[float] = field(init=False, repr=False)

    def __post_init__(self) -> None:
        # deque(maxlen=...) automatically drops the oldest value when full.
        if self.window_size < 1:
            raise ValueError("window_size must be at least 1")
        self._values = deque(maxlen=self.window_size)

    def add(self, value: float) -> float:
        """Add a value and return the updated average."""
        self._values.append(value)
        return self.average

    @property
    def average(self) -> float:
        """Current average; empty windows return 0 for simple display behavior."""
        if not self._values:
            return 0.0
        return sum(self._values) / len(self._values)
