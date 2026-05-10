import pytest
import asyncio
from unittest.mock import AsyncMock

from app.retry_handler import ExponentialBackoffRetry


@pytest.fixture
def retry_handler():
  """Create a retry handler with test configuration."""
  return ExponentialBackoffRetry(
    initial_delay=0.01,
    multiplier=2.0,
    max_delay=0.1,
    max_attempts=5,
  )


@pytest.mark.asyncio
async def test_succeeds_on_first_attempt(retry_handler):
  """Test that successful first attempt returns immediately without retries."""
  mock_func = AsyncMock(return_value={"result": "success"})
  
  result = await retry_handler.execute_with_backoff(mock_func)
  
  assert result == {"result": "success"}
  assert mock_func.call_count == 1


@pytest.mark.asyncio
async def test_retries_and_succeeds_eventually(retry_handler):
  """Test that function retries and succeeds after initial failures."""
  mock_func = AsyncMock()
  mock_func.side_effect = [
    Exception("Fail 1"),
    Exception("Fail 2"),
    {"result": "success"},
  ]
  
  result = await retry_handler.execute_with_backoff(mock_func)
  
  assert result == {"result": "success"}
  assert mock_func.call_count == 3


@pytest.mark.asyncio
async def test_fails_after_max_attempts(retry_handler):
  """Test that function raises exception after exhausting max_attempts."""
  mock_func = AsyncMock(side_effect=RuntimeError("Persistent failure"))
  
  with pytest.raises(RuntimeError, match="Persistent failure"):
    await retry_handler.execute_with_backoff(mock_func)
  
  assert mock_func.call_count == 5  # max_attempts


@pytest.mark.asyncio
async def test_backoff_delays_increase_exponentially(retry_handler, monkeypatch):
  """Test that backoff delays increase exponentially."""
  sleep_calls = []
  
  async def mock_sleep(delay):
    sleep_calls.append(delay)
  
  monkeypatch.setattr(asyncio, "sleep", mock_sleep)
  
  mock_func = AsyncMock()
  mock_func.side_effect = [
    Exception("Fail 1"),
    Exception("Fail 2"),
    Exception("Fail 3"),
    Exception("Fail 4"),
    Exception("Fail 5"),
  ]
  
  with pytest.raises(Exception, match="Fail 5"):
    await retry_handler.execute_with_backoff(mock_func)
  
  # Should have 4 sleep calls (one after each failure except the last)
  assert len(sleep_calls) == 4
  
  # Verify exponential growth: 0.01, 0.02, 0.04, 0.08
  expected_delays = [0.01, 0.02, 0.04, 0.08]
  for actual, expected in zip(sleep_calls, expected_delays):
    assert abs(actual - expected) < 0.001


@pytest.mark.asyncio
async def test_backoff_respects_max_delay(retry_handler, monkeypatch):
  """Test that backoff delays are capped at max_delay."""
  sleep_calls = []
  
  async def mock_sleep(delay):
    sleep_calls.append(delay)
  
  monkeypatch.setattr(asyncio, "sleep", mock_sleep)
  
  mock_func = AsyncMock()
  # Fail 5 times to trigger all backoff delays
  mock_func.side_effect = [
    Exception("Fail 1"),
    Exception("Fail 2"),
    Exception("Fail 3"),
    Exception("Fail 4"),
    Exception("Fail 5"),
  ]
  
  with pytest.raises(Exception, match="Fail 5"):
    await retry_handler.execute_with_backoff(mock_func)
  
  assert len(sleep_calls) == 4
  
  # All delays should be capped at max_delay (0.1)
  # Expected without capping: 0.01, 0.02, 0.04, 0.08
  # With capping at 0.1: 0.01, 0.02, 0.04, 0.08 (none exceed 0.1)
  for delay in sleep_calls:
    assert delay <= 0.1


@pytest.mark.asyncio
async def test_passes_args_and_kwargs(retry_handler):
  """Test that args and kwargs are properly passed to the async function."""
  mock_func = AsyncMock(return_value={"result": "success"})
  
  result = await retry_handler.execute_with_backoff(
    mock_func,
    "arg1",
    "arg2",
    kwarg1="value1",
    kwarg2="value2",
  )
  
  assert result == {"result": "success"}
  mock_func.assert_called_once_with(
    "arg1",
    "arg2",
    kwarg1="value1",
    kwarg2="value2",
  )


@pytest.mark.asyncio
async def test_max_attempts_configurable(retry_handler):
  """Test that max_attempts is configurable."""
  custom_retry_handler = ExponentialBackoffRetry(max_attempts=2)
  mock_func = AsyncMock(side_effect=RuntimeError("Persistent failure"))
  
  with pytest.raises(RuntimeError, match="Persistent failure"):
    await custom_retry_handler.execute_with_backoff(mock_func)
  
  # Should only attempt 2 times (not the default 5)
  assert mock_func.call_count == 2
