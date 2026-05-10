import pytest
from http import HTTPStatus as status
from unittest.mock import AsyncMock, MagicMock, patch

from app.agent_server import create_app
from app.translator import LinkProvisioningTranslator


@pytest.mark.asyncio
async def test_translator_validate_request_valid():
  """Test that a valid provisioning request passes validation."""
  translator = LinkProvisioningTranslator()
  payload = {
    "target_node": "node-2",
    "qos_level": "high",
    "duration_seconds": 300,
  }
  
  is_valid, error = translator.validate_request(payload)
  assert is_valid is True
  assert error is None


@pytest.mark.asyncio
async def test_translator_validate_request_missing_fields():
  """Test that missing required fields returns error."""
  translator = LinkProvisioningTranslator()
  payload = {
    "target_node": "node-2",
    # missing qos_level
  }
  
  is_valid, error = translator.validate_request(payload)
  assert is_valid is False
  assert "qos_level" in error


@pytest.mark.asyncio
async def test_translator_validate_request_invalid_qos():
  """Test that invalid QoS level returns error."""
  translator = LinkProvisioningTranslator()
  payload = {
    "target_node": "node-2",
    "qos_level": "ultra",  # not supported
  }
  
  is_valid, error = translator.validate_request(payload)
  assert is_valid is False
  assert "qos_level" in error


@pytest.mark.asyncio
async def test_translator_validate_request_empty_target_node():
  """Test that empty target_node returns error."""
  translator = LinkProvisioningTranslator()
  payload = {
    "target_node": "",
    "qos_level": "high",
  }
  
  is_valid, error = translator.validate_request(payload)
  assert is_valid is False
  assert "target_node" in error


@pytest.mark.asyncio
async def test_translator_validate_request_invalid_duration():
  """Test that invalid duration_seconds returns error."""
  translator = LinkProvisioningTranslator()
  payload = {
    "target_node": "node-2",
    "qos_level": "high",
    "duration_seconds": -1,  # negative
  }
  
  is_valid, error = translator.validate_request(payload)
  assert is_valid is False
  assert "duration_seconds" in error


@pytest.mark.asyncio
async def test_translator_validate_request_sets_default_key_rate():
  """Test validation derives key_rate_required from qos_level when omitted."""
  translator = LinkProvisioningTranslator()
  payload = {
    "target_node": "node-2",
    "qos_level": "high",
  }

  is_valid, error = translator.validate_request(payload)
  assert is_valid is True
  assert error is None
  assert payload["key_rate_required"] == 50


@pytest.mark.asyncio
async def test_translator_map_to_kms_command():
  """Test mapping high-level request to KMS command."""
  translator = LinkProvisioningTranslator()
  payload = {
    "target_node": "node-2",
    "qos_level": "high",
  }
  
  kms_command = translator.map_to_kms_command(payload)
  
  assert "link_id" in kms_command
  assert kms_command["target_node"] == "node-2"
  assert kms_command["sla_level"] == "critical"  # high QoS → critical SLA
  assert kms_command["key_rate_required"] == 50  # high → 5 * 10


@pytest.mark.asyncio
async def test_translator_map_to_kms_command_with_explicit_key_rate():
  """Test mapping with explicit key_rate_required."""
  translator = LinkProvisioningTranslator()
  payload = {
    "target_node": "node-2",
    "qos_level": "high",
    "key_rate_required": 100,
  }
  
  kms_command = translator.map_to_kms_command(payload)
  
  assert kms_command["key_rate_required"] == 100


@pytest.mark.asyncio
async def test_translator_map_to_kms_command_with_link_id():
  """Test mapping with explicit link_id."""
  translator = LinkProvisioningTranslator()
  payload = {
    "target_node": "node-2",
    "qos_level": "low",
  }
  
  kms_command = translator.map_to_kms_command(payload, link_id="custom-link-1")
  
  assert kms_command["link_id"] == "custom-link-1"
  assert kms_command["sla_level"] == "normal"  # low QoS → normal SLA
  assert kms_command["key_rate_required"] == 10  # low → 1 * 10


@pytest.mark.asyncio
async def test_provision_link_endpoint_success(aiohttp_client):
  """Test successful provisioning via endpoint."""
  app = create_app()
  client = await aiohttp_client(app)
  
  # Mock agent.provision_link to return success
  agent = app["sdn_agent"]
  agent.provision_link = AsyncMock(return_value={
    "status": "success",
    "link_id": "link-abc123",
    "eskr_consumed": 50,
  })
  
  payload = {
    "target_node": "node-2",
    "qos_level": "high",
  }
  
  resp = await client.post('/api/ui/provision_link', json=payload)
  assert resp.status == 200
  data = await resp.json()
  assert data["status"] == "success"
  assert data["link_id"] == "link-abc123"
  assert data["eskr_consumed"] == 50


@pytest.mark.asyncio
async def test_provision_link_endpoint_validation_error(aiohttp_client):
  """Test provisioning with invalid payload."""
  app = create_app()
  client = await aiohttp_client(app)
  
  payload = {
    "target_node": "node-2",
    # missing qos_level
  }
  
  resp = await client.post('/api/ui/provision_link', json=payload)
  assert resp.status == 400
  data = await resp.json()
  assert data["status"] == "failed"
  assert "qos_level" in data["error"]


@pytest.mark.asyncio
async def test_provision_link_endpoint_invalid_qos(aiohttp_client):
  """Test provisioning with invalid QoS level."""
  app = create_app()
  client = await aiohttp_client(app)
  
  payload = {
    "target_node": "node-2",
    "qos_level": "ultra_high",  # not supported
  }
  
  resp = await client.post('/api/ui/provision_link', json=payload)
  assert resp.status == 400
  data = await resp.json()
  assert data["status"] == "failed"
  assert "qos_level" in data["error"]


@pytest.mark.asyncio
async def test_provision_link_endpoint_kms_failure(aiohttp_client):
  """Test provisioning when KMS returns failure."""
  app = create_app()
  client = await aiohttp_client(app)
  
  # Mock agent.provision_link to return failure
  agent = app["sdn_agent"]
  agent.provision_link = AsyncMock(return_value={
    "status": "failed",
    "error": "insufficient_eskr",
    "reason": "insufficient_eskr",
  })
  
  payload = {
    "target_node": "node-2",
    "qos_level": "high",
  }
  
  resp = await client.post('/api/ui/provision_link', json=payload)
  assert resp.status == 400
  data = await resp.json()
  assert data["status"] == "failed"
  assert "insufficient_eskr" in data.get("error", "")


@pytest.mark.asyncio
async def test_provision_link_endpoint_kms_unreachable(aiohttp_client):
  """Test provisioning when KMS is unreachable."""
  app = create_app()
  client = await aiohttp_client(app)
  
  # Mock agent.provision_link to raise exception
  agent = app["sdn_agent"]
  agent.provision_link = AsyncMock(side_effect=Exception("Connection refused"))
  
  payload = {
    "target_node": "node-2",
    "qos_level": "high",
  }
  
  resp = await client.post('/api/ui/provision_link', json=payload)
  assert resp.status == 503
  data = await resp.json()
  assert data["status"] == "failed"
  assert data["error"] == "kms_unreachable"


@pytest.mark.asyncio
async def test_provision_link_endpoint_invalid_json(aiohttp_client):
  """Test provisioning with invalid JSON."""
  app = create_app()
  client = await aiohttp_client(app)
  
  resp = await client.post(
    '/api/ui/provision_link',
    data="not json",
    headers={"Content-Type": "application/json"}
  )
  assert resp.status == 400
  data = await resp.json()
  assert data["status"] == "failed"
  assert data["error"] == "invalid_json"


@pytest.mark.asyncio
async def test_provision_link_endpoint_qos_low(aiohttp_client):
  """Test provisioning with low QoS level."""
  app = create_app()
  client = await aiohttp_client(app)
  
  # Mock agent.provision_link to return success
  agent = app["sdn_agent"]
  agent.provision_link = AsyncMock(return_value={
    "status": "success",
    "link_id": "link-def456",
    "eskr_consumed": 10,
  })
  
  payload = {
    "target_node": "node-3",
    "qos_level": "low",
  }
  
  resp = await client.post('/api/ui/provision_link', json=payload)
  assert resp.status == 200
  data = await resp.json()
  assert data["status"] == "success"
  
  # Verify the KMS command was mapped correctly
  call_args = agent.provision_link.call_args
  kms_command = call_args[0][0]
  assert kms_command["sla_level"] == "normal"
  assert kms_command["key_rate_required"] == 10


@pytest.mark.asyncio
async def test_provision_link_endpoint_qos_normal(aiohttp_client):
  """Test provisioning with normal QoS level."""
  app = create_app()
  client = await aiohttp_client(app)
  
  # Mock agent.provision_link
  agent = app["sdn_agent"]
  agent.provision_link = AsyncMock(return_value={
    "status": "success",
    "link_id": "link-ghi789",
    "eskr_consumed": 20,
  })
  
  payload = {
    "target_node": "node-4",
    "qos_level": "normal",
  }
  
  resp = await client.post('/api/ui/provision_link', json=payload)
  assert resp.status == 200
  
  # Verify the KMS command was mapped correctly
  call_args = agent.provision_link.call_args
  kms_command = call_args[0][0]
  assert kms_command["sla_level"] == "high"
  assert kms_command["key_rate_required"] == 20
