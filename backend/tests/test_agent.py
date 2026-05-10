import pytest

from app.sdn_agent import SDNAgent


@pytest.mark.asyncio
async def test_sdn_agent_state_accessors_round_trip():
  agent = SDNAgent()

  state = {
    "nodes": [{"node_id": "node-1", "eskr_available": 7, "active_links": 1}],
    "active_links": {"L1": {"target_node": "node-2"}},
    "link_history": [{"link_id": "L1", "status": "success"}],
  }
  health = {
    "status": "healthy",
    "timestamp": "2026-05-10T10:00:00Z",
  }

  agent.set_local_state(state)
  agent.set_health_status(health)

  assert agent.get_local_state() == state
  assert agent.get_health_status() == health


@pytest.mark.asyncio
async def test_sdn_agent_start_and_close_manage_session():
  agent = SDNAgent()

  await agent.start()
  assert agent._kms_client is not None
  assert not agent._kms_client.closed
  assert agent._poll_task is not None

  await agent.close()
  assert agent._kms_client.closed
