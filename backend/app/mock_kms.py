import asyncio
import uuid
from copy import deepcopy


class MockKMS:
  MAX_ESKR_POOL = 100
  NODE_ID = "node-1"
  SUPPORTED_SLA_LEVELS = ("critical", "high", "normal")

  def __init__(self):
    self._eskr_pool = 0
    self._active_links = {}
    self._lock = asyncio.Lock()
    self._generate_key_task = None
  
  async def close(self):
    if self._generate_key_task is None:
      return

    self._generate_key_task.cancel()
    try:
      await self._generate_key_task
    except asyncio.CancelledError:
      pass

  async def start(self):
    if self._generate_key_task is None or self._generate_key_task.done():
      self._generate_key_task = asyncio.create_task(self._generate_keys())

  async def get_status(self):
    async with self._lock:
      return {
        "status": "online",
        "eskr_available": self._eskr_pool,
        "active_links": len(self._active_links),
      }

  async def get_capabilities(self):
    return {
      "node_id": self.NODE_ID,
      "max_eskr_pool": self.MAX_ESKR_POOL,
      "supported_sla_levels": list(self.SUPPORTED_SLA_LEVELS),
    }

  async def provision_link(self, configuration):
    link_id = configuration.get("link_id") or str(uuid.uuid4())

    raw_key_rate = configuration.get("key_rate_required", 0)
    if isinstance(raw_key_rate, bool) or not isinstance(raw_key_rate, (int, float)):
      raise ValueError("key_rate_required must be a number greater than 0")

    key_rate_required = int(raw_key_rate)

    if key_rate_required <= 0:
      raise ValueError("key_rate_required must be greater than 0")

    async with self._lock:
      if key_rate_required > self._eskr_pool:
        return {
          "status": "failed",
          "link_id": link_id,
          "eskr_consumed": 0,
          "reason": "insufficient_eskr",
        }

      self._eskr_pool -= key_rate_required
      self._active_links[link_id] = deepcopy(configuration)

      return {
        "status": "success",
        "link_id": link_id,
        "eskr_consumed": key_rate_required,
      }
  
  async def _generate_keys(self):
    while True:
      async with self._lock:
        if self._eskr_pool < self.MAX_ESKR_POOL:
          self._eskr_pool += 1
      await asyncio.sleep(0.1)
  
  async def get_eskr(self):
    async with self._lock:
      return self._eskr_pool
  
  async def get_active_links(self):
    async with self._lock:
      return deepcopy(self._active_links)
  
  async def get_active_links_len(self):
    async with self._lock:
      return len(self._active_links)

  async def get_health(self):
    async with self._lock:
      return {
        "status": "healthy",
        "eskr_available": self._eskr_pool,
        "active_links": len(self._active_links),
      }