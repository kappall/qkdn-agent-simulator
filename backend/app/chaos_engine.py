"""
Chaos Engine for Fault Injection

This module provides fault injection capabilities for testing system resilience.
It allows controlled injection of various fault types into the system.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Set, Optional
from datetime import datetime, timedelta
import random
import asyncio
import uuid

from app.logger import setup_logging


logger = setup_logging(__name__)


class FaultType(Enum):
  """Enum of fault types that can be injected."""
  NETWORK_TIMEOUT = "network_timeout"
  CONNECTION_REFUSED = "connection_refused"
  HTTP_500 = "http_500"
  HTTP_429 = "http_429"
  MALFORMED_RESPONSE = "malformed_response"
  PARTIAL_RESPONSE = "partial_response"
  LATENCY = "latency"
  TRANSIENT_ERROR = "transient_error"


class EndpointFilter(Enum):
  """Enum for endpoint filtering in chaos engine."""
  ALL = "all"
  PROVISION_LINK = "provision_link"
  FETCH_KMS_STATUS = "fetch_kms_status"
  POLL_KMS = "poll_kms"


@dataclass
class ChaosConfig:
  """Configuration for a chaos fault injection."""
  fault_type: FaultType
  probability: float
  affected_endpoints: Set[EndpointFilter] = field(default_factory=lambda: {EndpointFilter.ALL})
  duration_seconds: Optional[float] = None
  latency_ms: int = 0  # For LATENCY fault type
  error_details: Optional[str] = None
  
  def __post_init__(self):
    """Validate configuration."""
    if not 0.0 <= self.probability <= 1.0:
      raise ValueError(f"Probability must be between 0.0 and 1.0, got {self.probability}")
    if self.duration_seconds is not None and self.duration_seconds <= 0:
      raise ValueError(f"Duration must be positive, got {self.duration_seconds}")
    if self.latency_ms < 0:
      raise ValueError(f"Latency must be non-negative, got {self.latency_ms}")


@dataclass
class InjectedFault:
  """Represents an actively injected fault."""
  fault_id: str
  config: ChaosConfig
  created_at: datetime
  expires_at: Optional[datetime]
  injection_count: int = 0
  trigger_count: int = 0


class ChaosInjectionError(Exception):
  """Exception raised when chaos injection is triggered."""
  def __init__(self, fault_type: FaultType, details: Optional[str] = None):
    self.fault_type = fault_type
    self.details = details or str(fault_type.value)
    super().__init__(f"Chaos injection triggered: {self.details}")


class ChaosEngine:
  """
  Chaos Engine for fault injection.
  
  Manages fault injection, tracks statistics, and provides methods
  to query whether faults should be applied to specific operations.
  """
  
  def __init__(self, enabled: bool = True):
    """Initialize the chaos engine."""
    self._enabled = enabled
    self._active_faults: Dict[str, InjectedFault] = {}
    self._lock = asyncio.Lock()
    self._global_stats = {
      "total_injections": 0,
      "total_triggers": 0,
      "faults_by_type": {},
    }
    logger.info("Chaos Engine initialized (enabled=%s)", enabled)
  
  def set_enabled(self, enabled: bool) -> None:
    """Enable or disable the chaos engine."""
    self._enabled = enabled
    logger.info("Chaos Engine %s", "enabled" if enabled else "disabled")
  
  def is_enabled(self) -> bool:
    """Check if chaos engine is enabled."""
    return self._enabled
  
  async def inject_fault(self, config: ChaosConfig) -> str:
    """
    Inject a new fault into the system.
    
    Args:
      config: ChaosConfig with fault parameters
        
    Returns:
      fault_id: Unique identifier for the injected fault
        
    Raises:
      ValueError: If configuration is invalid
    """
    if not self._enabled:
      logger.warning("Attempt to inject fault but chaos engine is disabled")
      return ""
    
    fault_id = str(uuid.uuid4())
    now = datetime.now()
    expires_at = (
      now + timedelta(seconds=config.duration_seconds)
      if config.duration_seconds
      else None
    )
    
    fault = InjectedFault(
      fault_id=fault_id,
      config=config,
      created_at=now,
      expires_at=expires_at,
    )
    
    async with self._lock:
      self._active_faults[fault_id] = fault
      logger.info(
        "Fault injected: %s (type=%s, probability=%.2f, endpoint_filter=%s)",
        fault_id,
        config.fault_type.value,
        config.probability,
        [e.value for e in config.affected_endpoints],
      )
    
    return fault_id
  
  async def remove_fault(self, fault_id: str) -> bool:
    """
    Remove an injected fault.
    
    Args:
      fault_id: ID of the fault to remove
        
    Returns:
      True if fault was removed, False if not found
    """
    async with self._lock:
      if fault_id in self._active_faults:
        fault = self._active_faults.pop(fault_id)
        logger.info(
          "Fault removed: %s (type=%s, triggered %d times)",
          fault_id,
          fault.config.fault_type.value,
          fault.trigger_count,
        )
        return True
    
    logger.warning("Attempted to remove non-existent fault: %s", fault_id)
    return False
  
  async def clear_all_faults(self) -> int:
    """
    Clear all injected faults.
    
    Returns:
      Number of faults cleared
    """
    async with self._lock:
      count = len(self._active_faults)
      self._active_faults.clear()
      logger.info("Cleared all %d faults", count)
    
    return count
  
  async def should_inject_fault(
    self,
    endpoint: EndpointFilter,
  ) -> Optional[FaultType]:
    """
    Check if a fault should be injected for the given endpoint.
    
    This method:
    1. Checks if chaos engine is enabled
    2. Gets applicable faults for the endpoint
    3. Removes expired faults
    4. Applies probability-based fault selection
    5. Updates statistics
    
    Args:
      endpoint: The endpoint being called
        
    Returns:
      FaultType to inject, or None if no fault should be injected
    """
    if not self._enabled:
      return None
    
    async with self._lock:
      now = datetime.now()
      expired_ids = [
        fault_id
        for fault_id, fault in self._active_faults.items()
        if fault.expires_at and fault.expires_at <= now
      ]
      
      for fault_id in expired_ids:
        fault = self._active_faults.pop(fault_id)
        logger.info(
          "Fault expired: %s (type=%s)",
          fault_id,
          fault.config.fault_type.value,
        )
      

      applicable_faults = [
        fault
        for fault in self._active_faults.values()
        if (
          EndpointFilter.ALL in fault.config.affected_endpoints
          or endpoint in fault.config.affected_endpoints
        )
      ]
      
      if not applicable_faults:
        return None
      
      # Apply probability-based selection
      for fault in applicable_faults:
        if random.random() < fault.config.probability:
          fault.injection_count += 1
          fault.trigger_count += 1
          self._global_stats["total_injections"] += 1
          
          fault_type_str = fault.config.fault_type.value
          self._global_stats["faults_by_type"][fault_type_str] = (
            self._global_stats["faults_by_type"].get(fault_type_str, 0) + 1
          )
          
          logger.debug(
            "Fault triggered: %s (type=%s, endpoint=%s)",
            fault.fault_id,
            fault.config.fault_type.value,
            endpoint.value,
          )
          
          return fault.config.fault_type
      
      return None
  
  async def get_active_faults(self) -> List[Dict]:
    """
    Get list of all active faults.
    
    Returns:
      List of fault information dictionaries
    """
    async with self._lock:
      faults = []
      now = datetime.now()

      expired_ids = [
        fault_id
        for fault_id, fault in self._active_faults.items()
        if fault.expires_at and fault.expires_at <= now
      ]
    
      for fault_id in expired_ids:
        fault = self._active_faults.pop(fault_id)
        logger.info(
          "Fault expired: %s (type=%s)",
          fault_id,
          fault.config.fault_type.value,
        )
      
      for fault_id, fault in self._active_faults.items():
        age_seconds = (now - fault.created_at).total_seconds()
        remaining_seconds = (
          (fault.expires_at - now).total_seconds()
          if fault.expires_at
          else None
        )
          
        faults.append({
          "fault_id": fault_id,
          "fault_type": fault.config.fault_type.value,
          "probability": fault.config.probability,
          "affected_endpoints": [e.value for e in fault.config.affected_endpoints],
          "age_seconds": age_seconds,
          "remaining_seconds": remaining_seconds,
          "injection_count": fault.injection_count,
          "trigger_count": fault.trigger_count,
          "latency_ms": fault.config.latency_ms,
        })
      
      return sorted(faults, key=lambda x: x["age_seconds"])
  
  async def get_statistics(self) -> Dict:
    """
    Get chaos injection statistics.
    
    Returns:
      Dictionary with statistics
    """
    async with self._lock:
      return {
        "enabled": self._enabled,
        "active_faults": len(self._active_faults),
        "total_injections": self._global_stats["total_injections"],
        "total_triggers": self._global_stats["total_triggers"],
        "faults_by_type": self._global_stats["faults_by_type"].copy(),
      }
  
  async def get_fault_details(self, fault_id: str) -> Optional[Dict]:
    """
    Get details about a specific fault.
    
    Args:
      fault_id: The fault ID to query
        
    Returns:
      Fault details or None if not found
    """
    async with self._lock:
      fault = self._active_faults.get(fault_id)
      if not fault:
        return None
      
      now = datetime.now()
      age_seconds = (now - fault.created_at).total_seconds()
      remaining_seconds = (
        (fault.expires_at - now).total_seconds()
        if fault.expires_at
        else None
      )
      
      return {
        "fault_id": fault_id,
        "fault_type": fault.config.fault_type.value,
        "probability": fault.config.probability,
        "affected_endpoints": [e.value for e in fault.config.affected_endpoints],
        "age_seconds": age_seconds,
        "remaining_seconds": remaining_seconds,
        "injection_count": fault.injection_count,
        "trigger_count": fault.trigger_count,
        "latency_ms": fault.config.latency_ms,
        "error_details": fault.config.error_details,
      }
