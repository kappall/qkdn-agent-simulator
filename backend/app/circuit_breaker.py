from dataclasses import dataclass
from enum import Enum
from time import monotonic


class CircuitState(str, Enum):
  CLOSED = "CLOSED"
  OPEN = "OPEN"
  HALF_OPEN = "HALF_OPEN"


@dataclass
class CircuitBreakerStatus:
  state: str
  failure_count: int
  last_failure_time: float | None


class CircuitBreaker:
  def __init__(self, failure_threshold: int, reset_timeout_seconds: int):
    self._failure_threshold = failure_threshold
    self._reset_timeout_seconds = reset_timeout_seconds
    self._state = CircuitState.CLOSED
    self._failure_count = 0
    self._last_failure_time: float | None = None

  def can_execute(self) -> bool:
    if self._state == CircuitState.CLOSED:
      return True

    if self._state == CircuitState.OPEN:
      if self._last_failure_time is None:
        return False

      if monotonic() - self._last_failure_time >= self._reset_timeout_seconds:
        self._state = CircuitState.HALF_OPEN
        return True

      return False

    return True

  def record_success(self) -> None:
    self._state = CircuitState.CLOSED
    self._failure_count = 0
    self._last_failure_time = None

  def record_failure(self) -> None:
    self._failure_count += 1
    self._last_failure_time = monotonic()

    if self._state == CircuitState.HALF_OPEN or self._failure_count >= self._failure_threshold:
      self._state = CircuitState.OPEN

  def get_state(self) -> str:
    return self._state.value

  def get_status(self) -> dict:
    return {
      "state": self.get_state(),
      "failure_count": self._failure_count,
      "last_failure_time": self._last_failure_time,
    }