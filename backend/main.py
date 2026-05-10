import asyncio
import signal
from aiohttp import web

from app.kms_server import app as kms_app
from app.agent_server import create_app
from app.config import KMS_PORT, AGENT_PORT
from app.logger import setup_logging

logger = setup_logging("main")


async def run_all_services():
  loop = asyncio.get_running_loop()

  kms_runner = web.AppRunner(kms_app)
  await kms_runner.setup()
  kms_site = web.TCPSite(kms_runner, '127.0.0.1', KMS_PORT)
  await kms_site.start()
  logger.info(f"Mock KMS started on 127.0.0.1:{KMS_PORT}")

  agent_app = create_app()
  agent_runner = web.AppRunner(agent_app)
  await agent_runner.setup()
  agent_site = web.TCPSite(agent_runner, '127.0.0.1', AGENT_PORT)
  await agent_site.start()
  logger.info(f"SDN Agent started on 127.0.0.1:{AGENT_PORT}")

  stop_event = asyncio.Event()

  def _signal_handler():
    logger.info("Shutdown signal received")
    stop_event.set()

  for s in (signal.SIGINT, signal.SIGTERM):
    try:
      loop.add_signal_handler(s, _signal_handler)
    except NotImplementedError:
      pass

  await stop_event.wait()

  logger.info("Stopping services...")
  await agent_runner.cleanup()
  await kms_runner.cleanup()


def main():
  try:
    asyncio.run(run_all_services())
  except KeyboardInterrupt:
    logger.info("Interrupted by user")


if __name__ == '__main__':
  main()
