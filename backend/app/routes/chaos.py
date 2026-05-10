"""
Chaos Engine API Routes

Provides HTTP endpoints for controlling fault injection in the system.
"""

from aiohttp import web
from http import HTTPStatus as status
from typing import Optional

from app.logger import setup_logging
from app.chaos_engine import (
  FaultType,
  EndpointFilter,
  ChaosConfig,
)


routes = web.RouteTableDef()
logger = setup_logging("chaos_server")


def _parse_fault_type(fault_type_str: str) -> Optional[FaultType]:
  """Parse fault type from string."""
  try:
    return FaultType[fault_type_str.upper()]
  except (KeyError, AttributeError):
    return None


def _parse_endpoint_filters(endpoints_list) -> set:
  """Parse endpoint filters from list of strings."""
  if not endpoints_list:
    return {EndpointFilter.ALL}
  
  filters = set()
  for endpoint_str in endpoints_list:
    try:
      filters.add(EndpointFilter[endpoint_str.upper()])
    except (KeyError, AttributeError):
      pass
  
  return filters if filters else {EndpointFilter.ALL}


@routes.post('/api/chaos/inject')
async def inject_fault_handler(request):
  """
  Inject a fault into the system.
  
  POST /api/chaos/inject
  {
    "fault_type": "network_timeout",
    "probability": 0.5,
    "duration_seconds": 30,
    "affected_endpoints": ["provision_link", "fetch_kms_status"],
    "latency_ms": 100,
    "error_details": "Optional error message"
  }
  
  Returns:
  {
    "status": "success",
    "fault_id": "uuid-string"
  }
  """
  logger.info("Chaos inject endpoint called")
  chaos_engine = request.app.get("chaos_engine")
  
  if not chaos_engine:
    logger.error("Chaos engine not available")
    return web.json_response(
      status=status.INTERNAL_SERVER_ERROR,
      data={
        "status": "failed",
        "error": "chaos_engine_unavailable",
      },
    )
  
  try:
    payload = await request.json()
  except Exception as exc:
    logger.error("Failed to parse JSON: %s", exc)
    return web.json_response(
        status=status.BAD_REQUEST,
        data={"status": "failed", "error": "invalid_json"},
    )
  
  fault_type_str = payload.get("fault_type")
  if not fault_type_str:
    logger.warning("Missing fault_type in request")
    return web.json_response(
      status=status.BAD_REQUEST,
      data={"status": "failed", "error": "missing_fault_type"},
    )
  
  fault_type = _parse_fault_type(fault_type_str)
  if not fault_type:
    logger.warning("Invalid fault_type: %s", fault_type_str)
    return web.json_response(
      status=status.BAD_REQUEST,
      data={
        "status": "failed",
        "error": "invalid_fault_type",
        "valid_types": [ft.value for ft in FaultType],
      },
    )
  
  probability = payload.get("probability", 1.0)
  if not isinstance(probability, (int, float)) or not 0.0 <= probability <= 1.0:
    logger.warning("Invalid probability: %s", probability)
    return web.json_response(
      status=status.BAD_REQUEST,
      data={"status": "failed", "error": "invalid_probability"},
    )
  
  duration_seconds = payload.get("duration_seconds")
  if duration_seconds is not None:
    if not isinstance(duration_seconds, (int, float)) or duration_seconds <= 0:
      logger.warning("Invalid duration_seconds: %s", duration_seconds)
      return web.json_response(
        status=status.BAD_REQUEST,
        data={"status": "failed", "error": "invalid_duration"},
      )
  
  latency_ms = payload.get("latency_ms", 0)
  if not isinstance(latency_ms, int) or latency_ms < 0:
    logger.warning("Invalid latency_ms: %s", latency_ms)
    return web.json_response(
      status=status.BAD_REQUEST,
      data={"status": "failed", "error": "invalid_latency"},
    )
  
  affected_endpoints = _parse_endpoint_filters(payload.get("affected_endpoints"))
  
  try:
    config = ChaosConfig(
      fault_type=fault_type,
      probability=probability,
      affected_endpoints=affected_endpoints,
      duration_seconds=duration_seconds,
      latency_ms=latency_ms,
      error_details=payload.get("error_details"),
    )
    
    fault_id = await chaos_engine.inject_fault(config)
    
    logger.info("Fault injected successfully: %s", fault_id)
    return web.json_response(
      status=status.OK,
      data={
        "status": "success",
        "fault_id": fault_id,
      },
    )
  
  except ValueError as exc:
    logger.warning("Invalid configuration: %s", exc)
    return web.json_response(
      status=status.BAD_REQUEST,
      data={"status": "failed", "error": str(exc)},
    )


@routes.delete('/api/chaos/inject/{fault_id}')
async def remove_fault_handler(request):
  """
  Remove an injected fault.
  
  DELETE /api/chaos/inject/{fault_id}
  
  Returns:
  {
    "status": "success" | "not_found"
  }
  """
  fault_id = request.match_info.get("fault_id")
  logger.info("Chaos remove endpoint called for fault: %s", fault_id)
  chaos_engine = request.app.get("chaos_engine")
  
  if not chaos_engine:
    logger.error("Chaos engine not available")
    return web.json_response(
      status=status.INTERNAL_SERVER_ERROR,
      data={"status": "failed", "error": "chaos_engine_unavailable"},
    )
  
  removed = await chaos_engine.remove_fault(fault_id)
  
  if removed:
    return web.json_response(
      status=status.OK,
      data={"status": "success"},
    )
  else:
    return web.json_response(
      status=status.NOT_FOUND,
      data={"status": "not_found"},
    )


@routes.get('/api/chaos/active')
async def active_faults_handler(request):
  """
  Get list of active faults.
  
  GET /api/chaos/active
  
  Returns:
  {
    "status": "success",
    "faults": [
      {
        "fault_id": "uuid",
        "fault_type": "network_timeout",
        "probability": 0.5,
        "affected_endpoints": ["provision_link"],
        "age_seconds": 10,
        "remaining_seconds": 20,
        "injection_count": 5,
        "trigger_count": 3,
        "latency_ms": 100
      }
    ]
  }
  """
  logger.info("Chaos active faults endpoint called")
  chaos_engine = request.app.get("chaos_engine")
  
  if not chaos_engine:
    logger.error("Chaos engine not available")
    return web.json_response(
      status=status.INTERNAL_SERVER_ERROR,
      data={"status": "failed", "error": "chaos_engine_unavailable"},
    )
  
  faults = await chaos_engine.get_active_faults()
  
  return web.json_response(
    status=status.OK,
    data={
      "status": "success",
      "faults": faults,
    },
  )


@routes.get('/api/chaos/inject/{fault_id}')
async def fault_details_handler(request):
  """
  Get details about a specific fault.
  
  GET /api/chaos/inject/{fault_id}
  
  Returns fault details or 404 if not found.
  """
  fault_id = request.match_info.get("fault_id")
  logger.info("Chaos fault details endpoint called for: %s", fault_id)
  chaos_engine = request.app.get("chaos_engine")
  
  if not chaos_engine:
    logger.error("Chaos engine not available")
    return web.json_response(
      status=status.INTERNAL_SERVER_ERROR,
      data={"status": "failed", "error": "chaos_engine_unavailable"},
    )
  
  fault_details = await chaos_engine.get_fault_details(fault_id)
  
  if fault_details:
    return web.json_response(
      status=status.OK,
      data={
          "status": "success",
          "fault": fault_details,
      },
    )
  else:
    return web.json_response(
      status=status.NOT_FOUND,
      data={"status": "not_found"},
    )


@routes.get('/api/chaos/stats')
async def chaos_stats_handler(request):
  """
  Get chaos engine statistics.
  
  GET /api/chaos/stats
  
  Returns:
  {
    "status": "success",
    "stats": {
      "enabled": true,
      "active_faults": 2,
      "total_injections": 15,
      "total_triggers": 12,
      "faults_by_type": {
        "network_timeout": 8,
        "http_500": 4
      }
    }
  }
  """
  logger.info("Chaos stats endpoint called")
  chaos_engine = request.app.get("chaos_engine")
  
  if not chaos_engine:
    logger.error("Chaos engine not available")
    return web.json_response(
      status=status.INTERNAL_SERVER_ERROR,
      data={"status": "failed", "error": "chaos_engine_unavailable"},
    )
  
  stats = await chaos_engine.get_statistics()
  
  return web.json_response(
    status=status.OK,
    data={
      "status": "success",
      "stats": stats,
    },
  )


@routes.delete('/api/chaos/clear')
async def clear_faults_handler(request):
  """
  Clear all injected faults.
  
  DELETE /api/chaos/clear
  
  Returns:
  {
    "status": "success",
    "cleared_count": 3
  }
  """
  logger.info("Chaos clear endpoint called")
  chaos_engine = request.app.get("chaos_engine")
  
  if not chaos_engine:
    logger.error("Chaos engine not available")
    return web.json_response(
      status=status.INTERNAL_SERVER_ERROR,
      data={"status": "failed", "error": "chaos_engine_unavailable"},
    )
  
  cleared_count = await chaos_engine.clear_all_faults()
  
  return web.json_response(
    status=status.OK,
    data={
      "status": "success",
      "cleared_count": cleared_count,
    },
  )


@routes.get('/api/chaos/enabled')
async def chaos_enabled_handler(request):
  """
  Check if chaos engine is enabled.
  
  GET /api/chaos/enabled
  
  Returns:
  {
    "status": "success",
    "enabled": true
  }
  """
  logger.info("Chaos enabled status endpoint called")
  chaos_engine = request.app.get("chaos_engine")
  
  if not chaos_engine:
    logger.error("Chaos engine not available")
    return web.json_response(
      status=status.INTERNAL_SERVER_ERROR,
      data={"status": "failed", "error": "chaos_engine_unavailable"},
    )
  
  return web.json_response(
    status=status.OK,
    data={
      "status": "success",
      "enabled": chaos_engine.is_enabled(),
    },
  )


@routes.post('/api/chaos/enable')
async def enable_chaos_handler(request):
  """Enable the chaos engine."""
  logger.info("Chaos enable endpoint called")
  chaos_engine = request.app.get("chaos_engine")
  
  if not chaos_engine:
    logger.error("Chaos engine not available")
    return web.json_response(
      status=status.INTERNAL_SERVER_ERROR,
      data={"status": "failed", "error": "chaos_engine_unavailable"},
    )
  
  chaos_engine.set_enabled(True)
  return web.json_response(
    status=status.OK,
    data={"status": "success"},
  )


@routes.post('/api/chaos/disable')
async def disable_chaos_handler(request):
  """Disable the chaos engine."""
  logger.info("Chaos disable endpoint called")
  chaos_engine = request.app.get("chaos_engine")
  
  if not chaos_engine:
    logger.error("Chaos engine not available")
    return web.json_response(
      status=status.INTERNAL_SERVER_ERROR,
      data={"status": "failed", "error": "chaos_engine_unavailable"},
    )
  
  chaos_engine.set_enabled(False)
  return web.json_response(
    status=status.OK,
    data={"status": "success"},
  )
