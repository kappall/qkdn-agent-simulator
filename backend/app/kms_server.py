from aiohttp import web
from app.logger import setup_logging
from app.config import KMS_PORT
from app.routes.kms import kms, routes

logger = setup_logging(__name__)


app = web.Application()
app.add_routes(routes)


async def start_mock_kms(app):
  logger.info("Starting Mock KMS background task")
  await kms.start()


async def stop_mock_kms(app):
  logger.info("Stopping Mock KMS background task")
  await kms.close()


app.on_startup.append(start_mock_kms)
app.on_cleanup.append(stop_mock_kms)

if __name__ == '__main__':
  logger.info(f"Starting Mock KMS Server on port {KMS_PORT}...")
  web.run_app(app, host='127.0.0.1', port=KMS_PORT)
