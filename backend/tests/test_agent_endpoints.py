import pytest


from app.agent_server import create_app


@pytest.mark.asyncio
async def test_nodes_endpoint(aiohttp_client):
  app = create_app()
  client = await aiohttp_client(app)

  resp = await client.get('/api/ui/nodes')
  assert resp.status == 200
  data = await resp.json()
  assert 'nodes' in data
  assert isinstance(data['nodes'], list)


@pytest.mark.asyncio
async def test_health_endpoint(aiohttp_client):
  app = create_app()
  client = await aiohttp_client(app)

  resp = await client.get('/health')
  assert resp.status == 200
  data = await resp.json()
  assert 'status' in data
  assert data['status'] in ('idle', 'healthy', 'degraded')
