# tools/dev_server: REFERENCE / FALLBACK server

> **Not `server/`.** This is for A to adopt into `server/`, and a demo fallback if `server/`
> isn't ready. A owns the real server. Nothing in `web/` depends on this folder.

A small, complete server built to `CONTRACTS.md` v2.1 (branch `docs/contract-v2.1`) around B's
detector. It's one file, `aegis_dev_server.py`, about 300 lines. It uses the same routes, tokens
and close codes as A's skeleton in `server/aegis_server/`, so each part can be copied across
directly.

| Contract | What it does here |
|---|---|
| C1 | Forwards every caption to elder listeners just before the detector's events for it |
| C3 | `WS /captions/{id}` (laptop only) takes `caption`, `set_elder`, `end`. `WS /events/{id}?role=&token=` takes `set_elder` and `codeword_result` from the elder screen |
| C4 | `role=family` gets only `alert`, `intervention`, `codeword_ok`, `status`, `call_ended`. One token per role; a wrong or expired token closes with `4401` |
| C5 | `end` or `POST /sessions/{id}/end` → `call_ended` to everyone, then the tokens stop working |
| C6 | A listener that connects or reconnects gets that role's past events first (memory only) |
| C12 | `codeword_result.ok` must be a real bool (issue #10) |
| AI layer | On only if `GROQ_API_KEY` or `GEMINI_API_KEY` is set, using B's pattern from `detection/INTEGRATION.md` |
| Typed fallback | `POST /typed {session_id, text, speaker_raw}` becomes a final caption with `source:"typed"` |

There's no microphone or Deepgram here. That stays in A's `server/`.

## Run it

From the repo root:

```
pip install -e detection fastapi "uvicorn[standard]"
uvicorn aegis_dev_server:app --app-dir tools/dev_server --port 8000
```

Start a call. Both links are printed by the server and returned as JSON:

```
curl -s -X POST localhost:8000/sessions -H 'content-type: application/json' \
     -d '{"name":"Rose","phone":"+15550100"}'
```

Open `elder_url` on the laptop and `family_url` on the phone. Then send captions over
`ws://localhost:8000/captions/<id>`, or type the call:

```
python tools/dev_server/typed_cli.py            # new session, prints links, then type:
c: Grandma, it's me. Please don't tell Mom.
c: I need bail money right now. Gift cards only.
e: What's our family code word?
end
```

Or type one line at a time with curl:

```
curl -s -X POST localhost:8000/typed -H 'content-type: application/json' \
     -d '{"session_id":"<id>","text":"I need bail money right now","speaker_raw":"1"}'
```

`POST /sessions`, `/typed`, `/sessions/{id}/end` and `WS /captions` only accept the laptop
itself (127.0.0.1). The phone reaches only `/events`, through the web app's proxy, with its token.

## Tests

```
pip install pytest httpx
cd tools/dev_server && pytest -q
```

The tests cover tokens and 4401, captions before highlights, the family filter, `codeword_result`
over `/events` (wrong answer → hangup, right answer → `codeword_ok`), replay for a late family
page, `/typed`, `call_ended` followed by tokens expiring, and refusing other machines.

## What A would change when adopting it

- Captions from Deepgram, not just `/captions` and `/typed`.
- Settings from `server/.env` (`WEB_BASE_URL`, keys) instead of `os.environ`.
- Ending idle sessions after a timeout. Here a session lives until `end`.
