from aiohttp import web

from app.config import AGENT_PORT
from app.logger import setup_logging
from app.sdn_agent import SDNAgent

logger = setup_logging("agent_server")

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
  ])
  app.on_startup.append(on_startup)
  app.on_cleanup.append(on_cleanup)
  return app


app = create_app()

if __name__ == '__main__':
  logger.info(f"Starting SDN Agent Server on port {AGENT_PORT}...")
  web.run_app(app, host='127.0.0.1', port=AGENT_PORT)
