import pytest

from app.agent_server import create_app


@pytest.mark.asyncio
async def test_agent_status_endpoint(aiohttp_client):
  app = create_app()
  client = await aiohttp_client(app)

  resp = await client.get('/api/ui/status')
  assert resp.status == 200

  data = await resp.json()
  assert data['status'] == 'ok'
  assert data['service'] == 'SDN Agent'
  assert data['agent_status'] == 'idle'
