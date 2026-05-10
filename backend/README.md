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

- Mock KMS status: `http://127.0.0.1:8027/api/status`
- Agent nodes: `http://127.0.0.1:8028/api/ui/nodes`
- Agent status: `http://127.0.0.1:8028/api/ui/status`
- Agent health: `http://127.0.0.1:8028/health`

Example curls
-------------

```bash
curl http://127.0.0.1:8027/api/status
curl http://127.0.0.1:8028/api/ui/nodes
```

Notes
-----
- `main.py` starts the Mock KMS (port 8027) and the SDN Agent (port 8028) together.
- If you run services separately, ensure ports don't collide.
- Stop running services with Ctrl-C.

Docker
------

Build the image locally:

```bash
cd backend
docker build -t qkdn-backend:local .
```

Run with Docker (single container):

```bash
docker run --rm -p 8027:8027 -p 8028:8028 qkdn-backend:local
```

Or use `docker-compose`:

```bash
cd backend
docker-compose up --build
```
