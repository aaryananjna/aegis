# Aegis server (role A)

FastAPI server between the mic, B's detector (`detection/`) and C's screens (`web/`).
Built to `CONTRACTS.md` v2.1. Built: live calls (sessions, captions, routing, replay, AI layer), live Deepgram captions and
family accounts (TigerDB).

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
| `aegis_server/netguard.py` | Laptop-only check: loopback **and** no proxy/tunnel headers |
| `aegis_server/routes/sessions.py` | `GET /health`, `POST /sessions`, `POST /sessions/{id}/end`, `POST /typed` |
| `aegis_server/routes/captions_ws.py` | `WS /captions/{session_id}` (laptop only) |
| `aegis_server/routes/events_ws.py` | `WS /events/{session_id}?role=…&token=…` |
| `aegis_server/routes/auth.py` | Family accounts: `POST /auth/signup`, `/auth/login`, `/auth/logout`, `GET /auth/me` |
| `aegis_server/routes/elders.py` | Grandparents and pairing: `POST /elders`, `/elders/{id}/members`, `/elders/{id}/devices`, `DELETE /elders/{id}/devices`, `GET /device/me` |
| `aegis_server/security.py` | argon2id password hashes; random tokens stored only as sha256 |
| `aegis_server/seed.py` | Demo accounts with made-up names (`python -m aegis_server.seed`) |
| `aegis_server/migrate.py` | Applies `migrations/*.sql` to TigerDB |
| `aegis_server/stt/deepgram.py` | Laptop mic → Deepgram → `caption` events, in the server or as its own process |
| `aegis_server/stt/captions.py` | Deepgram results → contract captions |
| `aegis_server/db.py` | TigerDB connection (step 5) |

## Live captions (Deepgram)

```
pip install -e "server[mic]"                       # sounddevice, for the laptop mic
cd server
python -m aegis_server.stt.deepgram --list-devices
python -m aegis_server.stt.deepgram <session_id>   # mic -> Deepgram -> ws://localhost:8000/captions/<id>
python -m aegis_server.stt.deepgram <session_id> --file call.wav --show   # a WAV, in real time
```

Works with this server or with `tools/dev_server` (same `/captions` route). Needs
`DEEPGRAM_API_KEY` in `server/.env`. Options: `--device N`, `--server ws://host:port`,
`--end` (end the call on exit), `--no-diarize`, `--show` (print final lines; off by default so
caption text isn't logged). It prints how far captions trail speech when it stops.

Deepgram Nova-3 with interim results, speaker labels and `mip_opt_out=true`. `stt/captions.py`
turns each result into captions: one per speaker run, `utterance_id` `u<stretch>-<run>`,
`revision` rising on each interim. Audio is never written to disk.
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

## Starting a call

```
curl -s -X POST localhost:8000/sessions -H 'content-type: application/json' \
     -d '{"name":"Rose","phone":"+15550100","mic":true}'
```

`"mic": true` starts live captions from the laptop mic inside the server for this call
(`"device": "3"` picks a mic). Without it, send captions over `WS /captions/<id>` or `POST /typed`.
End with `POST /sessions/<id>/end`. Ending stops the mic, kills both tokens and drops the call's
history from memory.

## Who is the grandparent (no tap needed)

She's answering an incoming call, so the first line is normally her "Hello?". If the call's
first live line is a short greeting (5 words or fewer, in the first 30 s, with a speaker label),
the server picks that voice itself (`set_elder`). If the first line is long, it doesn't guess and
the screen asks for the tap. A tap always replaces the guess, and after a tap the server never
guesses. Elder screens get `{"type": "elder_set", "speaker_raw", "by": "server" | "tap"}`.
`AUTO_ELDER=0` turns the guess off. **Proposal:** waiting for B's and C's OK.

**Labels off** (`"labels": false` on `POST /sessions`): Deepgram's live speaker labels drift on
one laptop mic that hears both the phone speaker and the grandparent (a caller line can land
under her label and be ignored). With labels off, every line is scored from the start, with no
tap and no guess. Keep the grandparent's script lines free of scam words. The AI layer is off in
this mode (the detector needs a named grandparent for it).

## Security

**Where the voice goes:** laptop mic → server memory → Deepgram, over TLS with the certificate
checked, and nowhere else. No endpoint accepts or returns audio. Audio is never written to disk
or logged. Deepgram's model-improvement opt-out is on. The client refuses any audio destination
except `wss://api.deepgram.com` (or a local fake for tests). Only text captions come back, and
they only go to the elder screen.

**Laptop only** (`POST /sessions`, `/sessions/{id}/end`, `/typed`, `WS /captions`): the request
must come from loopback **and** carry no forwarding headers. The family phone's traffic comes
through the Cloudflare tunnel and Vite's proxy, so it also arrives on loopback; Cloudflare's
headers (`CF-Connecting-IP`, `X-Forwarded-For`) give it away. Refused: HTTP 403, or close 1008
on the socket.

**Screens** (`WS /events`):
- Each call gets two random 256-bit tokens, one per role, checked in constant time.
- A wrong token, the other role's token, an unknown call or an ended call all get the same
  close code, 4401.
- Family never gets captions, highlights or the risk meter.
- Inbound messages over 16 KB are dropped, and more than 20 a second closes the socket (1008).
- Each screen has its own outbox, so a slow phone can't stall the detector. A screen that falls
  2,000 events behind is dropped and gets the replay when it reconnects.

**Limits:** 8 calls at once, 4 screens per role per call (the oldest is dropped, so a phone that
reconnects always gets in), 2 hours per call.

**Everywhere:**
- Tokens are redacted from logs (`token=***`). Caption text is never logged.
- Responses carry `Cache-Control: no-store`, `Referrer-Policy: no-referrer`, a deny-all CSP and
  `X-Frame-Options: DENY`.
- CORS allows only `WEB_BASE_URL`. `/docs` is off unless `API_DOCS=1`.
- All outbound HTTPS (Deepgram, Groq, Gemini) checks certificates against `certifi`.
- Shutting down ends every live call.
