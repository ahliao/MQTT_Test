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
    window_size: int = 5
    _values: deque[float] = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if self.window_size < 1:
            raise ValueError("window_size must be at least 1")
        self._values = deque(maxlen=self.window_size)

    def add(self, value: float) -> float:
        self._values.append(value)
        return self.average

    @property
    def average(self) -> float:
        if not self._values:
            return 0.0
        return sum(self._values) / len(self._values)
