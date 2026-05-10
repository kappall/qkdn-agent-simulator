import pytest
from aiohttp import web

from app.routes.kms import routes, kms


async def make_app():
  app = web.Application()
  app.add_routes(routes)
  return app


@pytest.mark.asyncio
async def test_status_endpoint(aiohttp_client):
  app = await make_app()
  client = await aiohttp_client(app)

  kms._eskr_pool = 0
  kms._active_links = {}

  resp = await client.get('/api/status')
  assert resp.status == 200
  data = await resp.json()
  assert data['status'] == 'online'
  assert data['eskr_available'] == 0
  assert data['active_links'] == 0


@pytest.mark.asyncio
async def test_capabilities_endpoint(aiohttp_client):
  app = await make_app()
  client = await aiohttp_client(app)

  resp = await client.get('/api/capabilities')
  assert resp.status == 200
  data = await resp.json()
  assert data['node_id'] == kms.NODE_ID
  assert data['max_eskr_pool'] == kms.MAX_ESKR_POOL
  assert data['supported_sla_levels'] == list(kms.SUPPORTED_SLA_LEVELS)


@pytest.mark.asyncio
async def test_health_endpoint(aiohttp_client):
  app = await make_app()
  client = await aiohttp_client(app)

  kms._eskr_pool = 2
  kms._active_links = {}

  resp = await client.get('/health')
  assert resp.status == 200
  data = await resp.json()
  assert data['status'] == 'healthy'
  assert data['eskr_available'] == 2


@pytest.mark.asyncio
async def test_link_config_missing_fields(aiohttp_client):
  app = await make_app()
  client = await aiohttp_client(app)

  payload = {}
  resp = await client.post('/api/link_config', json=payload)
  assert resp.status == 400
  data = await resp.json()
  assert data['status'] == 'failed'
  assert data['error'] == 'missing_required_fields'
  assert set(data['missing_fields']) == set(("link_id", "target_node", "sla_level", "key_rate_required"))


@pytest.mark.asyncio
async def test_link_config_invalid_sla(aiohttp_client):
  app = await make_app()
  client = await aiohttp_client(app)

  payload = {
    'link_id': 'L1',
    'target_node': 'node-x',
    'sla_level': 'low',
    'key_rate_required': 1,
  }
  resp = await client.post('/api/link_config', json=payload)
  assert resp.status == 400
  data = await resp.json()
  assert data['status'] == 'failed'
  assert data['error'] == 'invalid_sla_level'
  assert 'supported_sla_levels' in data


@pytest.mark.asyncio
async def test_link_config_key_rate_value_error(aiohttp_client):
  app = await make_app()
  client = await aiohttp_client(app)

  payload = {
    'link_id': 'L2',
    'target_node': 'node-x',
    'sla_level': kms.SUPPORTED_SLA_LEVELS[0],
    'key_rate_required': 0,
  }
  resp = await client.post('/api/link_config', json=payload)
  assert resp.status == 400
  data = await resp.json()
  assert data['status'] == 'failed'
  assert 'key_rate_required must be greater than 0' in data['error']


@pytest.mark.asyncio
async def test_link_config_insufficient_eskr(aiohttp_client):
  app = await make_app()
  client = await aiohttp_client(app)

  kms._eskr_pool = 0
  kms._active_links = {}

  payload = {
    'link_id': 'L3',
    'target_node': 'node-x',
    'sla_level': kms.SUPPORTED_SLA_LEVELS[0],
    'key_rate_required': 1,
  }
  resp = await client.post('/api/link_config', json=payload)
  assert resp.status == 400
  data = await resp.json()
  assert data['status'] == 'failed'
  assert data['reason'] == 'insufficient_eskr'


@pytest.mark.asyncio
async def test_link_config_success(aiohttp_client):
  app = await make_app()
  client = await aiohttp_client(app)

  # provide enough eskrs
  kms._eskr_pool = 10
  kms._active_links = {}

  payload = {
    'link_id': 'L4',
    'target_node': 'node-x',
    'sla_level': kms.SUPPORTED_SLA_LEVELS[0],
    'key_rate_required': 5,
  }
  resp = await client.post('/api/link_config', json=payload)
  assert resp.status == 200
  data = await resp.json()
  assert data['status'] == 'success'
  assert data['link_id'] == 'L4'
  assert data['eskr_consumed'] == 5
