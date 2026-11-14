# web/ (role C): Aegis screens

Vite, React, TypeScript, Tailwind and React Router. Placeholder pages for now: each one only
lists the events it receives.

```
cd web
npm install
npm run dev          # http://localhost:5173
npm run build        # type-check and production build
```

## Pages and sources

| URL | What it shows |
|---|---|
| `/elder?fixture=scam-grandson` | sample scam call, replayed with its original timing |
| `/elder?fixture=benign-party` | sample normal call |
| `/family?fixture=scam-grandson` | only `alert`, `intervention`, `status`, `call_ended` (CONTRACTS C4) |
| `/evidence?fixture=scam-grandson` | everything, like `/elder` |
| `/elder?session=<id>&token=<token>` | live: `WS /events/<id>?role=elder&token=…` |

Add `&speed=4` to play a fixture faster.

Fixtures are in `public/fixtures/`, copied from `detection/fixtures/` on branch
`b/caption-fixtures`. Those versions include `caption` events.

## Live mode

The page connects to its own origin, and Vite forwards `/events` to A's server
(`AEGIS_SERVER`, default `http://localhost:8000`). Until `server/` exists, B's example server
works, though it doesn't forward captions yet (CONTRACTS C1):

```
pip install fastapi uvicorn && pip install -e detection
uvicorn server_example:app --app-dir detection/examples --port 8000
# open http://localhost:5173/elder?session=demo
# then send caption JSON to ws://localhost:8000/captions/demo
```

## Code

- `src/events/types.ts`: event types from `CONTRACTS.md` v2.1.
- `src/events/useEvents.ts`: `useEvents(feed)` returns `{events, connection, error, send}`.
  - It reconnects on its own and skips events it already has, so replays after a reconnect
    (CONTRACTS C6) are safe.
  - `send()` sends `set_elder` or `codeword_result` on the live socket.
- `src/events/fixturePlayer.ts`: plays a JSONL file by each event's `t`.
