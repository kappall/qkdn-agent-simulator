from aiohttp import web
from app.logger import setup_logging
from app.config import AGENT_PORT

logger = setup_logging("agent_server")

async def health_check(request):
  logger.info("Agent health check pinged")
  return web.json_response({"status": "ok", "service": "SDN Agent"})

app = web.Application()
app.add_routes([web.get('/api/ui/status', health_check)])

if __name__ == '__main__':
  logger.info(f"Starting SDN Agent Server on port {AGENT_PORT}...")
  web.run_app(app, host='127.0.0.1', port=AGENT_PORT)
