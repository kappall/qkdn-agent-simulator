# ait-qkdn-agent-simulator — backend

Quick start
-----------

```bash
cd backend
uv run python -m main
# or
python -m main
```

Run only the agent server (for dev):
```bash
cd backend
uv run -m app.agent_server
```

Run tests:

```bash
cd backend
uv run pytest -v
```

Default endpoints
-----------------

- Mock KMS status: `http://127.0.0.1:8000/api/status`
- Agent nodes: `http://127.0.0.1:8001/api/ui/nodes`
- Agent status: `http://127.0.0.1:8001/api/ui/status`
- Agent health: `http://127.0.0.1:8001/health`

Example curls
-------------

```bash
curl http://127.0.0.1:8000/api/status
curl http://127.0.0.1:8001/api/ui/nodes
```

Notes
-----
- `main.py` starts the Mock KMS (port 8000) and the SDN Agent (port 8001) together.
- If you run services separately, ensure ports don't collide.
- Stop running services with Ctrl-C.
