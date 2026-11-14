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
