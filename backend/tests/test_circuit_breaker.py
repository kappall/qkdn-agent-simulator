import pytest
from aiohttp import web

from app.circuit_breaker import CircuitBreaker
from app.routes.agent import routes
from app.sdn_agent import SDNAgent


class DummyKMSClient:
  def get(self, *_args, **_kwargs):
    raise AssertionError("KMS client should not be called when circuit is open")

  def post(self, *_args, **_kwargs):
    raise AssertionError("KMS client should not be called when circuit is open")


@pytest.mark.asyncio
async def test_circuit_breaker_opens_after_threshold(monkeypatch):
  from app import circuit_breaker as circuit_breaker_module

  times = iter([0.0, 1.0, 2.0, 3.0])
  monkeypatch.setattr(circuit_breaker_module, "monotonic", lambda: next(times))

  breaker = CircuitBreaker(failure_threshold=3, reset_timeout_seconds=30)

  breaker.record_failure()
  breaker.record_failure()
  breaker.record_failure()

  assert breaker.get_state() == "OPEN"
  assert breaker.can_execute() is False
  assert breaker.get_status()["failure_count"] == 3


@pytest.mark.asyncio
async def test_circuit_breaker_half_open_recovers_after_timeout(monkeypatch):
  from app import circuit_breaker as circuit_breaker_module

  current_time = [0.0]
  monkeypatch.setattr(circuit_breaker_module, "monotonic", lambda: current_time[0])

  breaker = CircuitBreaker(failure_threshold=3, reset_timeout_seconds=30)
  breaker.record_failure()
  breaker.record_failure()
  breaker.record_failure()

  assert breaker.get_state() == "OPEN"

  current_time[0] = 31.0
  assert breaker.can_execute() is True
  assert breaker.get_state() == "HALF_OPEN"

  breaker.record_success()
  assert breaker.get_state() == "CLOSED"
  assert breaker.get_status()["failure_count"] == 0


@pytest.mark.asyncio
async def test_agent_short_circuits_fetch_and_provision():
  agent = SDNAgent()
  agent._kms_client = DummyKMSClient()

  agent._circuit_breaker.record_failure()
  agent._circuit_breaker.record_failure()
  agent._circuit_breaker.record_failure()

  with pytest.raises(RuntimeError, match="Circuit breaker is open"):
    await agent.fetch_kms_status()

  with pytest.raises(RuntimeError, match="Circuit breaker is open"):
    await agent.provision_link({
      "link_id": "link-1",
      "target_node": "node-2",
      "sla_level": "high",
      "key_rate_required": 10,
    })


@pytest.mark.asyncio
async def test_circuit_breaker_status_endpoint(aiohttp_client):
  app = web.Application()
  agent = SDNAgent()
  agent._circuit_breaker.record_failure()
  agent._circuit_breaker.record_failure()
  app["sdn_agent"] = agent
  app.add_routes(routes)

  client = await aiohttp_client(app)

  resp = await client.get("/api/ui/circuit_breaker_status")
  assert resp.status == 200

  data = await resp.json()
  assert data["state"] == "CLOSED"
  assert data["failure_count"] == 2
  assert data["last_failure_time"] is not None
