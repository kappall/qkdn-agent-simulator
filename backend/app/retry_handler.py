import asyncio
import logging
from typing import Callable, Any

logger = logging.getLogger(__name__)


class ExponentialBackoffRetry:
  """
  Implements exponential backoff retry logic for async functions.
  
  Delays grow exponentially: initial_delay, initial_delay * multiplier, 
  initial_delay * multiplier^2, etc., capped at max_delay.
  
  Args:
    initial_delay: Starting delay in seconds (default 1.0)
    multiplier: Exponential growth factor (default 2.0)
    max_delay: Maximum delay cap in seconds (default 60.0)
    max_attempts: Maximum number of attempts (default 5)
  """
  
  def __init__(
    self,
    initial_delay: float = 1.0,
    multiplier: float = 2.0,
    max_delay: float = 60.0,
    max_attempts: int = 5,
  ):
    self.initial_delay = initial_delay
    self.multiplier = multiplier
    self.max_delay = max_delay
    self.max_attempts = max_attempts
  
  async def execute_with_backoff(
    self,
    async_func: Callable,
    *args: Any,
    **kwargs: Any,
  ) -> Any:
    """
    Execute an async function with exponential backoff retry logic.
    
    Args:
      async_func: Async function to call
      *args: Positional arguments to pass to async_func
      **kwargs: Keyword arguments to pass to async_func
    
    Returns:
      Result from async_func if successful
    
    Raises:
      Exception: Last exception encountered after max_attempts exhausted
    """
    last_exception = None
    
    for attempt in range(self.max_attempts):
      try:
        result = await async_func(*args, **kwargs)
        if attempt > 0:
          logger.info(
            f"Recovered after {attempt} retries for {async_func.__name__}"
          )
        return result
      except Exception as exc:
        last_exception = exc
        
        if attempt == self.max_attempts - 1:
          logger.error(
            f"Max attempts ({self.max_attempts}) reached for {async_func.__name__}. "
            f"Last error: {exc}"
          )
          raise
        
        delay = self.initial_delay * (self.multiplier ** attempt)
        delay = min(delay, self.max_delay)
        
        logger.debug(
          f"Attempt {attempt + 1} failed for {async_func.__name__}: {exc}. "
          f"Retrying in {delay:.1f}s..."
        )
        
        await asyncio.sleep(delay)
    
    if last_exception:
      raise last_exception
