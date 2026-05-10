from aiohttp import web
from http import HTTPStatus as status

from app.config import AGENT_PORT
from app.logger import setup_logging
from app.sdn_agent import SDNAgent
from app.translator import LinkProvisioningTranslator

logger = setup_logging("agent_server")
translator = LinkProvisioningTranslator()

async def health_check(request):
  logger.info("Agent health check pinged")
  agent = request.app["sdn_agent"]
  return web.json_response({
    "status": "ok",
    "service": "SDN Agent",
    "agent_status": agent.get_health_status()["status"],
  })


async def nodes_handler(request):
  logger.info("Agent nodes endpoint pinged")
  agent = request.app["sdn_agent"]
  return web.json_response({"nodes": agent.get_local_state().get("nodes", [])})


async def health_endpoint(request):
  logger.info("Agent health endpoint pinged")
  agent = request.app["sdn_agent"]
  return web.json_response(agent.get_health_status())


async def provision_link_handler(request):
  logger.info("Provision link endpoint called")
  agent = request.app["sdn_agent"]
  
  try:
    payload = await request.json()
  except Exception as exc:
    logger.error("Failed to parse JSON: %s", exc)
    return web.json_response(
      status=status.BAD_REQUEST,
      data={"status": "failed", "error": "invalid_json"},
    )
  
  is_valid, error_message = translator.validate_request(payload)
  if not is_valid:
    logger.warning("Invalid provisioning request: %s", error_message)
    return web.json_response(
      status=status.BAD_REQUEST,
      data={"status": "failed", "error": error_message},
    )
  
  kms_command = translator.map_to_kms_command(payload)
  logger.info("Mapped request to KMS command: %s", kms_command)
  
  try:
    result = await agent.provision_link(kms_command)
    
    if result.get("status") == "success":
      logger.info("Link provisioned successfully: %s", result.get("link_id"))
      return web.json_response(
        status=status.OK,
        data=result,
      )
    else:
      logger.warning("Link provisioning failed: %s", result.get("error"))
      return web.json_response(
        status=status.BAD_REQUEST,
        data=result,
      )
  except Exception as exc:
    logger.error("KMS provisioning call failed: %s", exc)
    return web.json_response(
      status=status.SERVICE_UNAVAILABLE,
      data={
        "status": "failed",
        "error": "kms_unreachable",
        "details": str(exc),
      },
    )

async def on_startup(app):
  await app["sdn_agent"].start()


async def on_cleanup(app):
  await app["sdn_agent"].close()


def create_app():
  app = web.Application()
  app["sdn_agent"] = SDNAgent()
  app.add_routes([
    web.get('/api/ui/status', health_check),
    web.get('/api/ui/nodes', nodes_handler),
    web.get('/health', health_endpoint),
    web.post('/api/ui/provision_link', provision_link_handler),
  ])
  app.on_startup.append(on_startup)
  app.on_cleanup.append(on_cleanup)
  return app


app = create_app()

if __name__ == '__main__':
  logger.info(f"Starting SDN Agent Server on port {AGENT_PORT}...")
  web.run_app(app, host='127.0.0.1', port=AGENT_PORT)
