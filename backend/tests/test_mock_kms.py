import pytest
import pytest_asyncio
import asyncio

from app.mock_kms import MockKMS


@pytest_asyncio.fixture
async def kms():
  """Create and start a MockKMS instance for testing."""
  kms_instance = MockKMS()
  await kms_instance.start()
  yield kms_instance
  await kms_instance.close()


@pytest.fixture
def kms_no_start():
  """Create a MockKMS instance without starting key generation."""
  return MockKMS()


class TestMockKMSStatus:
  """Tests for status endpoint and methods."""

  @pytest.mark.asyncio
  async def test_status_endpoint_returns_correct_format(self, kms):
    """Test: Status endpoint returns correct format."""
    status = await kms.get_status()
    
    assert isinstance(status, dict)
    assert "status" in status
    assert "eskr_available" in status
    assert "active_links" in status
    assert status["status"] == "online"
    assert isinstance(status["eskr_available"], int)
    assert isinstance(status["active_links"], int)

  @pytest.mark.asyncio
  async def test_status_initial_state(self, kms_no_start):
    """Test: Initial status shows 0 ESKR and no active links."""
    status = await kms_no_start.get_status()
    
    assert status["status"] == "online"
    assert status["eskr_available"] == 0
    assert status["active_links"] == 0


class TestMockKMSCapabilities:
  """Tests for capabilities endpoint."""

  @pytest.mark.asyncio
  async def test_capabilities_endpoint_returns_static_data(self, kms):
    """Test: Capabilities endpoint returns static data."""
    capabilities = await kms.get_capabilities()
    
    assert isinstance(capabilities, dict)
    assert "node_id" in capabilities
    assert "max_eskr_pool" in capabilities
    assert "supported_sla_levels" in capabilities
    
    assert capabilities["node_id"] == "node-1"
    assert capabilities["max_eskr_pool"] == 100
    assert capabilities["supported_sla_levels"] == ["critical", "high", "normal"]

  @pytest.mark.asyncio
  async def test_capabilities_are_consistent(self, kms):
    """Test: Multiple calls to capabilities return same data."""
    cap1 = await kms.get_capabilities()
    cap2 = await kms.get_capabilities()
    
    assert cap1 == cap2


class TestMockKMSKeyGeneration:
  """Tests for ESKR key generation."""

  @pytest.mark.asyncio
  async def test_eskr_generation_increases_over_time(self, kms):
    """Test: ESKR generation increases over time."""
    initial_eskr = await kms.get_eskr()
    
    await asyncio.sleep(0.25)  # at least 2 keys generated
    
    new_eskr = await kms.get_eskr()
    
    assert new_eskr > initial_eskr
    assert new_eskr >= initial_eskr + 2

  @pytest.mark.asyncio
  async def test_eskr_pool_respects_max_limit(self, kms):
    """Test: ESKR pool respects max limit (100)."""
    max_wait_time = 15  # 15 seconds should be enough to reach 100
    start_time = asyncio.get_event_loop().time()
    
    while True:
      current_eskr = await kms.get_eskr()
      if current_eskr >= MockKMS.MAX_ESKR_POOL:
        break
      
      elapsed = asyncio.get_event_loop().time() - start_time
      if elapsed > max_wait_time:
        pytest.fail(f"ESKR pool did not reach max of {MockKMS.MAX_ESKR_POOL} after {max_wait_time}s")
      
      await asyncio.sleep(0.5)
    
    final_eskr = await kms.get_eskr()
    assert final_eskr == MockKMS.MAX_ESKR_POOL
    
    await asyncio.sleep(0.3)
    after_max_eskr = await kms.get_eskr()
    assert after_max_eskr == MockKMS.MAX_ESKR_POOL


class TestMockKMSLinkProvisioning:
  """Tests for link provisioning logic."""

  @pytest.mark.asyncio
  async def test_link_config_consumes_keys_correctly(self, kms):
    """Test: Link config consumes keys correctly."""

    while (await kms.get_eskr()) < 50:
      await asyncio.sleep(0.1)
    
    initial_eskr = await kms.get_eskr()
    
    result = await kms.provision_link({
      "link_id": "link-test-1",
      "target_node": "node-2",
      "sla_level": "high",
      "key_rate_required": 10,
    })
    
    assert result["status"] == "success"
    assert result["link_id"] == "link-test-1"
    assert result["eskr_consumed"] == 10
    
    remaining_eskr = await kms.get_eskr()
    assert remaining_eskr == initial_eskr - 10

  @pytest.mark.asyncio
  async def test_link_config_fails_when_eskr_insufficient(self, kms_no_start):
    """Test: Link config fails when ESKR insufficient."""

    result = await kms_no_start.provision_link({
      "link_id": "link-test-2",
      "target_node": "node-2",
      "sla_level": "high",
      "key_rate_required": 10,
    })
    
    assert result["status"] == "failed"
    assert result["reason"] == "insufficient_eskr"
    assert result["eskr_consumed"] == 0

  @pytest.mark.asyncio
  async def test_link_config_raises_on_invalid_key_rate(self, kms_no_start):
    """Test: Link config raises ValueError for key_rate <= 0."""
    with pytest.raises(ValueError, match="key_rate_required must be greater than 0"):
      await kms_no_start.provision_link({
        "link_id": "link-test-3",
        "target_node": "node-2",
        "sla_level": "high",
        "key_rate_required": 0,
      })

  @pytest.mark.asyncio
  async def test_link_config_tracks_active_links(self, kms):
    """Test: Provisioned links are tracked in active_links."""
    while (await kms.get_eskr()) < 50:
      await asyncio.sleep(0.1)
    
    result1 = await kms.provision_link({
      "link_id": "link-1",
      "target_node": "node-2",
      "sla_level": "high",
      "key_rate_required": 10,
    })
    
    result2 = await kms.provision_link({
      "link_id": "link-2",
      "target_node": "node-3",
      "sla_level": "normal",
      "key_rate_required": 5,
    })
    
    assert result1["status"] == "success"
    assert result2["status"] == "success"
    
    active_links = await kms.get_active_links()
    assert len(active_links) == 2
    assert "link-1" in active_links
    assert "link-2" in active_links
    
    assert active_links["link-1"]["target_node"] == "node-2"
    assert active_links["link-2"]["target_node"] == "node-3"

  @pytest.mark.asyncio
  async def test_link_config_generates_uuid_if_no_link_id(self, kms):
    """Test: Link config generates UUID if link_id not provided."""
    while (await kms.get_eskr()) < 20:
      await asyncio.sleep(0.1)
    
    result = await kms.provision_link({
      "target_node": "node-2",
      "sla_level": "high",
      "key_rate_required": 5,
    })
    
    assert result["status"] == "success"
    assert "link_id" in result
    assert len(result["link_id"]) > 0
    
    active_links = await kms.get_active_links()
    assert result["link_id"] in active_links


class TestMockKMSHealth:
  """Tests for health check endpoint."""

  @pytest.mark.asyncio
  async def test_health_endpoint_returns_correct_format(self, kms):
    """Test: Health endpoint returns correct format."""
    health = await kms.get_health()
    
    assert isinstance(health, dict)
    assert "status" in health
    assert "eskr_available" in health
    assert "active_links" in health
    assert health["status"] == "healthy"
    assert isinstance(health["eskr_available"], int)
    assert isinstance(health["active_links"], int)

  @pytest.mark.asyncio
  async def test_health_reflects_current_state(self, kms):
    """Test: Health reflects current ESKR and active links."""
    # Fill up some ESKR
    while (await kms.get_eskr()) < 30:
      await asyncio.sleep(0.1)
    
    initial_health = await kms.get_health()
    initial_eskr = initial_health["eskr_available"]
    
    # Provision a link
    await kms.provision_link({
      "link_id": "link-health-test",
      "target_node": "node-2",
      "sla_level": "high",
      "key_rate_required": 5,
    })
    
    new_health = await kms.get_health()
    
    assert new_health["eskr_available"] == initial_eskr - 5
    assert new_health["active_links"] == 1


class TestMockKMSStartStop:
  """Tests for start/stop lifecycle."""

  @pytest.mark.asyncio
  async def test_kms_start_creates_generation_task(self):
    """Test: start() creates the key generation task."""
    kms = MockKMS()
    assert kms._generate_key_task is None
    
    await kms.start()
    assert kms._generate_key_task is not None
    assert not kms._generate_key_task.done()
    
    await kms.close()

  @pytest.mark.asyncio
  async def test_kms_close_cancels_generation_task(self):
    """Test: close() cancels the key generation task."""
    kms = MockKMS()
    await kms.start()
    
    task = kms._generate_key_task
    assert not task.done()
    
    await kms.close()
    assert task.done()

  @pytest.mark.asyncio
  async def test_kms_multiple_starts_dont_create_duplicate_tasks(self):
    """Test: Multiple starts don't create duplicate tasks."""
    kms = MockKMS()
    await kms.start()
    
    task1 = kms._generate_key_task
    
    await kms.start()
    
    task2 = kms._generate_key_task
    
    # Should be the same task
    assert task1 is task2
    
    await kms.close()
