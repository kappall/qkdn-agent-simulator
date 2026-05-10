from copy import deepcopy
import asyncio

import aiohttp

from app.config import KMS_URL
from app.logger import setup_logging


logger = setup_logging(__name__)


class SDNAgent:
  def __init__(self):
    self._kms_base_url = KMS_URL
    self._kms_client = None
    self._poll_task = None
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

    async with self._kms_client.get("/api/status") as response:
      response.raise_for_status()
      return await response.json()

  async def provision_link(self, kms_command: dict):
    """
    Provision a link via KMS.
    
    Args:
      kms_command: Dict with link_id, target_node, sla_level, key_rate_required
    
    Returns:
      Dict with KMS response (status, link_id, eskr_consumed, etc.)
    
    Raises:
      aiohttp.ClientError if KMS is unreachable
    """
    if self._kms_client is None:
      raise RuntimeError("SDNAgent must be started before provisioning")

    async with self._kms_client.post("/api/link_config", json=kms_command) as response:
      result = await response.json()
      
      # Track successful link in active_links and history
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
        # Track failed link in history
        link_id = kms_command.get("link_id", "unknown")
        self._local_state["link_history"].append({
          "link_id": link_id,
          "status": "failed",
          "target_node": kms_command.get("target_node"),
          "reason": result.get("error") or result.get("reason"),
          "timestamp": result.get("timestamp", ""),
        })
      
      return result
  
  async def _poll_kms(self):
    while True:
      try:
        kms_status = await self.fetch_kms_status()
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