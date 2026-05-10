from copy import deepcopy
import asyncio

import aiohttp

from app.circuit_breaker import CircuitBreaker
from app.config import (
  CIRCUIT_BREAKER_RESET_TIMEOUT,
  CIRCUIT_BREAKER_THRESHOLD,
  BACKOFF_INITIAL_DELAY,
  BACKOFF_MULTIPLIER,
  BACKOFF_MAX_DELAY,
  BACKOFF_MAX_ATTEMPTS,
  TOKEN_BUCKET_CAPACITY,
  TOKEN_BUCKET_REFILL_RATE,
  PROVISION_LINK_RATE_LIMIT,
  POLL_LINK_STATUS_RATE_LIMIT,
  KMS_STATUS_RATE_LIMIT,
  KMS_URL,
)
from app.rate_limiter import TokenBucketRateLimiter
from app.retry_handler import ExponentialBackoffRetry
from app.logger import setup_logging


logger = setup_logging(__name__)


class SDNAgent:
  def __init__(self):
    self._kms_base_url = KMS_URL
    self._kms_client = None
    self._poll_task = None
    self._circuit_breaker = CircuitBreaker(
      failure_threshold=CIRCUIT_BREAKER_THRESHOLD,
      reset_timeout_seconds=CIRCUIT_BREAKER_RESET_TIMEOUT,
    )
    self._retry_handler = ExponentialBackoffRetry(
      initial_delay=BACKOFF_INITIAL_DELAY,
      multiplier=BACKOFF_MULTIPLIER,
      max_delay=BACKOFF_MAX_DELAY,
      max_attempts=BACKOFF_MAX_ATTEMPTS,
    )
    self._provision_link_limiter = TokenBucketRateLimiter(
      max_tokens=PROVISION_LINK_RATE_LIMIT,
      refill_rate=PROVISION_LINK_RATE_LIMIT,
    )
    self._poll_status_limiter = TokenBucketRateLimiter(
      max_tokens=POLL_LINK_STATUS_RATE_LIMIT,
      refill_rate=POLL_LINK_STATUS_RATE_LIMIT,
    )
    self._kms_status_limiter = TokenBucketRateLimiter(
      max_tokens=KMS_STATUS_RATE_LIMIT,
      refill_rate=KMS_STATUS_RATE_LIMIT,
    )
    self._local_state = {
      "nodes": [],
      "active_links": {},
      "link_history": [],
    }
    self._health_status = {
      "status": "idle",
      "timestamp": None,
    }

  async def start(self):
    if self._kms_client is None or self._kms_client.closed:
      self._kms_client = aiohttp.ClientSession(base_url=self._kms_base_url)
    if self._poll_task is None or self._poll_task.done():
      self._poll_task = asyncio.create_task(self._poll_kms())

  async def close(self):
    if self._poll_task is not None and not self._poll_task.done():
      self._poll_task.cancel()
      try:
        await self._poll_task
      except asyncio.CancelledError:
        pass
    if self._kms_client is not None and not self._kms_client.closed:
      await self._kms_client.close()

  async def fetch_kms_status(self):
    if self._kms_client is None:
      raise RuntimeError("SDNAgent must be started before fetching KMS status")

    if not self._circuit_breaker.can_execute():
      raise RuntimeError("Circuit breaker is open")

    if not await self._kms_status_limiter.acquire(wait=False):
      raise RuntimeError("Rate limit exceeded for KMS status check")

    try:
      async with self._kms_client.get("/api/status") as response:
        if response.status >= 500:
          self._circuit_breaker.record_failure()
          body = await response.text()
          raise RuntimeError(f"KMS status request failed: {response.status} {body}")

        response.raise_for_status()
        result = await response.json()
        self._circuit_breaker.record_success()
        return result
    except (aiohttp.ClientError, asyncio.TimeoutError) as exc:
      self._circuit_breaker.record_failure()
      raise exc

  async def provision_link(self, kms_command: dict):
    """
    Provision a link via KMS.
    
    Args:
      kms_command: Dict with link_id, target_node, sla_level, key_rate_required
    
    Returns:
      Dict with KMS response (status, link_id, eskr_consumed, etc.)
    
    Raises:
      RuntimeError if rate limit exceeded or circuit breaker is open
      aiohttp.ClientError if KMS is unreachable
    """
    if self._kms_client is None:
      raise RuntimeError("SDNAgent must be started before provisioning")

    if not self._circuit_breaker.can_execute():
      raise RuntimeError("Circuit breaker is open")

    # Apply rate limiting
    if not await self._provision_link_limiter.acquire(wait=False):
      raise RuntimeError("Rate limit exceeded for provision_link endpoint")

    try:
      # Wrap the actual HTTP request with retry logic
      result = await self._retry_handler.execute_with_backoff(
        self._make_kms_provision_request,
        kms_command,
      )

      self._circuit_breaker.record_success()

      if result.get("status") == "success":
        link_id = result.get("link_id")
        self._local_state["active_links"][link_id] = {
          "target_node": kms_command.get("target_node"),
          "qos_level": kms_command.get("sla_level"),
          "established_at": result.get("timestamp", ""),
          "eskr_consumed": result.get("eskr_consumed", 0),
        }
        self._local_state["link_history"].append({
          "link_id": link_id,
          "status": "success",
          "target_node": kms_command.get("target_node"),
          "timestamp": result.get("timestamp", ""),
        })
      else:
        link_id = kms_command.get("link_id", "unknown")
        self._local_state["link_history"].append({
          "link_id": link_id,
          "status": "failed",
          "target_node": kms_command.get("target_node"),
          "reason": result.get("error") or result.get("reason"),
          "timestamp": result.get("timestamp", ""),
        })

      return result
    except (aiohttp.ClientError, asyncio.TimeoutError, RuntimeError) as exc:
      self._circuit_breaker.record_failure()
      raise exc

  async def _make_kms_provision_request(self, kms_command: dict):
    """
    Internal helper: makes the actual HTTP request to KMS for provisioning.
    
    Args:
      kms_command: Dict with link_id, target_node, sla_level, key_rate_required
    
    Returns:
      Dict with KMS response
    
    Raises:
      RuntimeError if response status >= 500
      aiohttp.ClientError if request fails
    """
    async with self._kms_client.post("/api/link_config", json=kms_command) as response:
      if response.status >= 500:
        body = await response.text()
        raise RuntimeError(f"KMS provisioning request failed: {response.status} {body}")
      
      result = await response.json()
      return result
  
  async def _poll_kms(self):
    while True:
      try:
        # Apply rate limiting to poll task
        await self._poll_status_limiter.acquire(wait=True)
        
        kms_status = await self._retry_handler.execute_with_backoff(
          self.fetch_kms_status
        )
        self.set_local_state({
          "nodes": [{
            "node_id": "node-1",
            "eskr_available": kms_status.get("eskr_available", 0),
            "active_links": kms_status.get("active_links", 0),
          }],
          "active_links": self._local_state["active_links"],
          "link_history": self._local_state["link_history"],
        })
        self.set_health_status({
          "status": "healthy",
          "timestamp": kms_status.get("timestamp"),
        })
      except (aiohttp.ClientError, asyncio.TimeoutError, RuntimeError) as exc:
        logger.warning("KMS poll failed: %s", exc)
        self.set_health_status({
          "status": "degraded",
          "timestamp": None,
        })
      await asyncio.sleep(2)

  def get_local_state(self):
    return deepcopy(self._local_state)

  def set_local_state(self, state):
    self._local_state = deepcopy(state)

  def get_health_status(self):
    return deepcopy(self._health_status)

  def set_health_status(self, health_status):
    self._health_status = deepcopy(health_status)

  def get_circuit_breaker_status(self):
    return deepcopy(self._circuit_breaker.get_status())