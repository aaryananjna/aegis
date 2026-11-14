# PR: `c/web-scaffold` → `main`

**Title:** `web: Vite + React + TS + Tailwind scaffold with useEvents()`

**Open it here:** https://github.com/aaryananjna/aegis/compare/main...c/web-scaffold?expand=1

---

## What changed

Adds `web/` (role C). Nothing outside `web/` changes, apart from this PR text in `docs/`.

- **Stack:** Vite 8.3.5, React 19.3.1, TypeScript 7.0.2, Tailwind 4.3.3 (Vite plugin),
  React Router 8.5.1. All versions are pinned exactly, and there's a lockfile.
- **`useEvents(feed)`** returns `{events, connection, error, send}`. There are two sources:
  - **Live:** `WS /events/{session_id}?role=elder|family&token=…`. The page connects to its own
    origin, and Vite forwards `/events` to `AEGIS_SERVER` (default `http://localhost:8000`).
    - It reconnects with backoff (0.5 to 5 s) and skips events it already has, so replays after
      a reconnect (CONTRACTS v2.1, C6) are safe.
    - It stops on close code `4401` (bad token) or after `call_ended`.
    - `send()` sends `set_elder` or `codeword_result`.
  - **Fixture:** `?fixture=scam-grandson` replays `public/fixtures/events-<name>.jsonl` at each
    event's `t`. Add `&speed=4` to go faster.
- **Family role:** both sources keep only `alert`, `intervention`, `status` and `call_ended`
  (C4).
- **Placeholder routes:** `/elder`, `/family` and `/evidence` only list the events they receive.
  The real screens come in follow-up PRs.
- **Types:** `src/events/types.ts` follows `CONTRACTS.md` v2.1 (branch `docs/contract-v2.1`,
  still a draft).
- **Fixtures:** copied from `origin/b/caption-fixtures`, so they include `caption` events.

## How I tested it

- `npm run build` (`tsc -b` and `vite build`) passes. `npm install` reports 0 vulnerabilities.
- In headless Chrome against `npm run dev`:
  - `/elder?fixture=scam-grandson`: all 23 events in file order, ends as `ended`.
  - `/family?fixture=scam-grandson`: only the 4 card and alert events.
  - `/elder?fixture=benign-party`: 8 events, no cards.
  - `/elder?fixture=nope`: shows "fixture not found".
- Live, against `detection/examples/server_example.py` on :8000 through the Vite proxy, with a
  script sending the scam call to `/captions/{sid}`:
  - `/elder`: 13 detector events.
  - `/family`: only the 4 card and alert events.
  - No captions arrive, because the example server doesn't forward them yet (C1).
- **Fix included:** under React StrictMode (dev), the first socket's late `onclose` cleared the
  shared socket ref after the second socket had connected, so `send()` silently failed. Now a
  socket only clears the ref if it still owns it. `send()` itself is exercised by the
  `/elder` screen in the stacked PR (`c/elder-screen`).

## Notes for reviewers

- Needs Node 22.12+ (built with Node 26.13.1 LTS): `cd web && npm install && npm run dev`.
- No API keys, no network calls except to the local server, and caption text is never logged.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
