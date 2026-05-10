"""
Token Bucket Rate Limiter Implementation

Provides rate limiting for SDN Agent endpoints using a token bucket algorithm.
Tokens are refilled at a configured rate per second, and requests consume tokens
to proceed. When the bucket is empty, requests are denied or must wait.
"""

import asyncio
import time

from app.logger import setup_logging

logger = setup_logging(__name__)


class TokenBucketRateLimiter:
  """
  Token bucket rate limiter for rate-limiting async operations.
  
  The token bucket algorithm works as follows:
  - A bucket holds up to `max_tokens` tokens
  - Tokens are added at `refill_rate` tokens per second
  - Each request consumes 1 token to proceed
  - If tokens are available, the request is granted immediately
  - If no tokens are available, the request can wait for tokens to be refilled
  
  Attributes:
      max_tokens (float): Maximum number of tokens the bucket can hold
      refill_rate (float): Rate at which tokens are refilled (tokens per second)
      _current_tokens (float): Current number of tokens in the bucket
      _last_refill_time (float): Timestamp of the last token refill
      _lock (asyncio.Lock): Lock to ensure thread-safe token updates
  """
  
  def __init__(self, max_tokens: float, refill_rate: float):
    """
    Initialize the token bucket rate limiter.
    
    Args:
      max_tokens: Maximum tokens in the bucket
      refill_rate: Tokens added per second
        
    Raises:
      ValueError: If max_tokens <= 0 or refill_rate <= 0
    """
    if max_tokens <= 0:
      raise ValueError("max_tokens must be positive")
    if refill_rate <= 0:
      raise ValueError("refill_rate must be positive")
    
    self.max_tokens = max_tokens
    self.refill_rate = refill_rate
    self._current_tokens = max_tokens
    self._last_refill_time = time.time()
    self._lock = asyncio.Lock()
    
    logger.info(
      f"TokenBucketRateLimiter initialized: "
      f"max_tokens={max_tokens}, refill_rate={refill_rate}/sec"
    )
  
  async def _refill(self) -> None:
    """
    Refill tokens based on elapsed time since last refill.
    
    This method calculates how many tokens should be added based on the
    time elapsed since the last refill, respecting the max_tokens limit.
    """
    current_time = time.time()
    elapsed = current_time - self._last_refill_time
    
    tokens_to_add = elapsed * self.refill_rate
    
    self._current_tokens = min(
      self.max_tokens,
      self._current_tokens + tokens_to_add
    )
    
    self._last_refill_time = current_time
  
  async def acquire(self, tokens: float = 1.0, wait: bool = False) -> bool:
    """
    Try to acquire tokens from the bucket.
    
    Args:
      tokens: Number of tokens to acquire (default: 1.0)
      wait: If True, wait for tokens to become available.
            If False, return immediately (default: False)
    
    Returns:
      True if tokens were acquired, False if not enough tokens and wait=False
        
    Raises:
      ValueError: If tokens <= 0
    """
    if tokens <= 0:
        raise ValueError("tokens must be positive")
    
    async with self._lock:
      await self._refill()
      
      if self._current_tokens >= tokens:
        self._current_tokens -= tokens
        logger.debug(
            f"Token acquired: {tokens} tokens consumed, "
            f"{self._current_tokens:.2f} remaining"
        )
        return True
      
      if not wait:
        logger.debug(
          f"Token request denied: requested {tokens}, "
          f"available {self._current_tokens:.2f}"
        )
        return False
    
    tokens_needed = tokens - self._current_tokens
    wait_time = tokens_needed / self.refill_rate
    
    logger.debug(
      f"Waiting {wait_time:.2f}s for {tokens_needed:.2f} tokens "
      f"({tokens} total requested)"
    )
    await asyncio.sleep(wait_time)
    
    # Try again after waiting
    async with self._lock:
      await self._refill()
      
      if self._current_tokens >= tokens:
        self._current_tokens -= tokens
        logger.info(
          f"Token acquired after wait: {tokens} tokens consumed, "
          f"{self._current_tokens:.2f} remaining"
        )
        return True
      
      # Should not reach here
      logger.warning(f"Token acquisition failed after wait period")
      return False
  
  async def get_available_tokens(self) -> float:
    """
    Get the current number of available tokens without acquiring them.
    
    Returns:
        Current number of tokens in the bucket
    """
    async with self._lock:
      await self._refill()
      return self._current_tokens

  async def reset(self) -> None:
    """
    Reset the bucket to max_tokens and reset the refill timer.
    
    Useful for testing or resetting the rate limiter state.
    """
    async with self._lock:
      self._current_tokens = self.max_tokens
      self._last_refill_time = time.time()
      logger.info(f"TokenBucketRateLimiter reset to {self.max_tokens} tokens")
