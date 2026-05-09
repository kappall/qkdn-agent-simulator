from aiohttp import web
from logger import setup_logging
from config import KMS_PORT

logger = setup_logging(__name__)

async def health_check(request):
  logger.info("KMS health check pinged")
  return web.json_response({"status": "ok", "service": "Mock KMS"})

app = web.Application()
app.add_routes([web.get('/api/v1/status', health_check)])

if __name__ == '__main__':
  logger.info(f"Starting Mock KMS Server on port {KMS_PORT}...")
  web.run_app(app, host='127.0.0.1', port=KMS_PORT)
