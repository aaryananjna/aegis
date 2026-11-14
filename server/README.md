# Aegis server (role A)

FastAPI server between the mic, B's detector (`detection/`) and C's screens (`web/`).
Built to `CONTRACTS.md` v2.1. Accounts and pairing work (TigerDB). Live-call endpoints are still skeletons (501 or close).

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
| `aegis_server/routes/auth.py` | Family accounts: `POST /auth/signup`, `/auth/login`, `/auth/logout`, `GET /auth/me` |
| `aegis_server/routes/elders.py` | Grandparents and pairing: `POST /elders`, `/elders/{id}/members`, `/elders/{id}/devices`, `DELETE /elders/{id}/devices`, `GET /device/me` |
| `aegis_server/security.py` | argon2id password hashes; random tokens stored only as sha256 |
| `aegis_server/seed.py` | Demo accounts with made-up names (`python -m aegis_server.seed`) |
| `aegis_server/migrate.py` | Applies `migrations/*.sql` to TigerDB |
| `aegis_server/stt/deepgram.py` | Laptop mic → Deepgram → `caption` events (step 2) |
| `aegis_server/db.py` | TigerDB connection pool (auth endpoints answer 503 without it) |

## Accounts (option D)

Family members log in; the grandparent never does. A family member creates the grandparent
(`POST /elders`, becoming owner), can add other signed-up family as viewers, and pairs the
grandparent's laptop once (`POST /elders/{id}/devices` returns a `device_token` and a
`pair_url` of the form `WEB_BASE_URL/pair#<token>`). The laptop sends the token as
`X-Device-Token`. Logging in sits alongside the per-call family link in `CONTRACTS.md`.

- The login token is an httpOnly, SameSite=Lax cookie `aegis_login`, valid for `LOGIN_DAYS`
  (7). From C's screens, call with `credentials: "include"`. Scripts may send
  `Authorization: Bearer <token>`.
- Errors: 401 not logged in or wrong password, 403 viewer trying an owner action, 404 a
  grandparent you don't watch, 409 duplicate email or member, 422 bad input, 429 too many attempts (with
  Retry-After), 503 no database.
- Limits (memory only, cleared on restart): 5 failed logins per email and 20 per client
  address per 15 min; 10 signups per client address per hour. Password hashing runs in a
  worker thread so logins never stall live calls.
- `pytest` runs the account tests against TigerDB in a throwaway schema that is dropped
  afterwards. They're skipped when `TIGER_DATABASE_URL` isn't set (for example in CI).
