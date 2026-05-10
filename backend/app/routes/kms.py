from aiohttp import web
from http import HTTPStatus as status

from app.mock_kms import MockKMS

routes = web.RouteTableDef()

kms = MockKMS()

@routes.get('/api/status')
async def get_status(request: web.Request):
  response = await kms.get_status()
  return web.json_response(status=status.OK, data=response)


@routes.get('/api/capabilities')
async def get_capabilities(request: web.Request):
  response = await kms.get_capabilities()
  return web.json_response(status=status.OK, data=response)


@routes.post('/api/link_config')
async def link_config(request: web.Request):
  payload = await request.json()

  required_fields = ("link_id", "target_node", "sla_level", "key_rate_required")
  missing_fields = [field for field in required_fields if field not in payload]
  if missing_fields:
    return web.json_response(
      status=status.BAD_REQUEST,
      data={
        "status": "failed",
        "error": "missing_required_fields",
        "missing_fields": missing_fields,
      },
    )

  if payload["sla_level"] not in kms.SUPPORTED_SLA_LEVELS:
    return web.json_response(
      status=status.BAD_REQUEST,
      data={
        "status": "failed",
        "error": "invalid_sla_level",
        "supported_sla_levels": list(kms.SUPPORTED_SLA_LEVELS),
      },
    )

  try:
    response = await kms.provision_link(payload)
  except ValueError as exc:
    return web.json_response(
      status=status.BAD_REQUEST,
      data={
        "status": "failed",
        "error": str(exc),
      },
    )

  if response["status"] == "failed":
    return web.json_response(status=status.BAD_REQUEST, data=response)

  return web.json_response(status=status.OK, data=response)


@routes.get('/health')
async def health_check(request: web.Request):
  response = await kms.get_health()
  return web.json_response(status=status.OK, data=response)