# web/ (role C): Aegis screens

Vite, React, TypeScript, Tailwind and React Router. `/elder` is the real grandparent screen.
`/family` and `/evidence` are still placeholders that list the events they receive.

```
cd web
npm install
npm run dev          # http://localhost:5173
npm run build        # type-check and production build
npm test             # screen logic tests (Node's built-in runner, no extra packages)
```

## Pages and sources

| URL | What it shows |
|---|---|
| `/elder?fixture=scam-grandson` | sample scam call, replayed with its original timing |
| `/elder?fixture=benign-party` | sample normal call |
| `/elder?fixture=demo-bank` | fake bank call: the `verify` card, then hang up |
| `/family?fixture=scam-grandson` | only `alert`, `intervention`, `status`, `call_ended` (CONTRACTS C4) |
| `/evidence?fixture=scam-grandson` | everything, like `/elder` |
| `/elder?session=<id>&token=<token>` | live: `WS /events/<id>?role=elder&token=…` |

Add `&speed=4` to play a fixture faster.

Fixtures are in `public/fixtures/`, copied from `detection/fixtures/` on `main`, so they
include `caption` events.

## The elder screen (`src/elder/`)

Laptop, landscape, read from about 2 m away.

- **Captions** take the top 60%. They show the last 4 lines at 48 px or larger.
  - An interim line is lighter and is replaced in place by a newer revision.
  - Highlights: a dotted underline while the line is still being spoken (provisional), a soft
    amber background once it's final.
  - A `typed` badge marks lines with `source: "typed"`.
- **Status band:** words only. "Normal call", "Be careful" or "Warning", from `risk.level`.
  Notes on the right: sample call, reconnecting, warnings.
- **One card** in the bottom 40%, latched (it never goes back):
  - `codeword`: two buttons, "They knew it" and "They didn't", that send `codeword_result`.
    After `codeword_ok` the card says so.
  - `verify`: text only.
  - `hangup`: a red card.
- **"Tap the voice that is you."** lists each voice with its latest line. A tap sends
  `set_elder`, and captions then read "You" and "Caller". If a card is already up, the picker
  shrinks into the status band.
- **Accessibility:**
  - captions are `aria-live="polite"` and cards are `aria-live="assertive"`
  - focus moves to a new card
  - every control is a real button
  - `prefers-reduced-motion` turns off the slow color change
- **Logic** lives in `state.ts` (a pure reducer, tested in `state.test.ts`).
- `demo-bank` was generated from `detection/demo/demo-scam.call` on `main` with
  `python -m hangup_detect.replay demo/demo-scam.call --json --captions`.

## Live mode

The page connects to its own origin, and Vite forwards `/events` to A's server
(`AEGIS_SERVER`, default `http://localhost:8000`). Until `server/` exists, B's example server
shows the detector's events, with two limits:
- It doesn't forward captions (CONTRACTS C1).
- It ignores what the screen sends on `/events`, namely `set_elder` and `codeword_result`
  (C3, C12). It reads those only on `/captions`.

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
