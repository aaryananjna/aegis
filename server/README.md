# Aegis server (role A)

FastAPI server between the mic, B's detector (`detection/`) and C's screens (`web/`).
Built to `CONTRACTS.md` v2.1. **Skeleton only:** endpoints exist but most return 501 or close.

## Run

```
python -m venv .venv && source .venv/bin/activate
pip install -e detection -e "server[dev]"
cp server/.env.example server/.env        # then fill in keys
uvicorn aegis_server.main:app --app-dir server --port 8000
cd server && pytest -q
```

## Layout

| File | What it owns |
|---|---|
| `aegis_server/main.py` | The FastAPI app; wires the routers |
| `aegis_server/config.py` | Settings from `.env` |
| `aegis_server/sessions.py` | One `Session` per call: detector, queue, owner task, ticker, tokens, listeners, replay history |
| `aegis_server/messages.py` | Checks inbound messages (`caption`, `set_elder`, `codeword_result`, `end`) |
| `aegis_server/roles.py` | Which events each role gets (C4) |
| `aegis_server/routes/sessions.py` | `GET /health`, `POST /sessions`, `POST /sessions/{id}/end` |
| `aegis_server/routes/captions_ws.py` | `WS /captions/{session_id}` (laptop only) |
| `aegis_server/routes/events_ws.py` | `WS /events/{session_id}?role=…&token=…` |
| `aegis_server/routes/auth.py` | `POST /auth/signup`, `/auth/login`, `/auth/logout` (TigerDB, step 5) |
| `aegis_server/stt/deepgram.py` | Laptop mic → Deepgram → `caption` events (step 2) |
| `aegis_server/db.py` | TigerDB connection (step 5) |
