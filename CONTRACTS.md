# Hang Up event contracts

**Version 2.1, DRAFT.** v2 was written by B (Mihir). The v2.1 additions are proposed by C
(Aaryan) after `docs/INTEGRATION_AUDIT.md`. **Needs an OK from A and B before anyone builds
against it as final.** Every v2.1 change is additive, so nothing that works today breaks.

Everything between the three parts travels as JSON over A's WebSockets.

> **V1 is archived.** The first plan (`call_id`/`t_ms`/`payload` envelope, UPPERCASE enums,
> `/api/inject-text`, vault) lives only on the branch `backup/my-original-docs`. No code uses it
> and it isn't coming back to `main`. Section 5 of `docs/INTEGRATION_AUDIT.md` compares the two.

## What changed in v2.1

| # | Change | Type |
|---|---|---|
| C1 | The server forwards every `caption` to elder-role listeners | ADDITIVE |
| C2 | Optional `caption.source`: `"live"` or `"typed"` | ADDITIVE |
| C3 | Transport written down: WebSocket paths, query params, which socket accepts which inbound message | ADDITIVE |
| C4 | `role=family` receives only `alert`, `intervention`, `status`, `call_ended`, with a token | ADDITIVE |
| C5 | Inbound `end` message and a new `call_ended` event | ADDITIVE |
| C6 | On connect or reconnect, the server replays that session's past events for the role | ADDITIVE |
| C7 | `status` is documented as warnings only, plus an optional `stt` field from the server | ADDITIVE |
| C8 | Doc fixes: the envelope covers B's events only, `none` is never sent, alerts carry ≤ 3 quotes, warning strings listed | ADDITIVE (docs only) |
| C12 | Inbound `codeword_result` from the elder screen after the code word card | ADDITIVE |

## Envelope

Every event **the detector emits** (`tactic_set`, `risk`, `intervention`, `alert`, `status`)
has `type`, `session_id`, `t` (seconds since the session started, detector clock, never goes
backwards) and `seq` (per session, starts at 1, always increasing).

Events the **server** adds (`caption` to screens, `call_ended`, `status` with `stt`) have
`type`, `session_id` and `t`, but **no `seq`**: `seq` only orders the detector's events. Screens
order by arrival.

Inbound messages (`caption` into the server, `set_elder`, `codeword_result`, `end`) need only
`type`. `session_id` is optional, because the session comes from the URL.

## Transport (C3)

Server base URL: `http://localhost:8000` on the laptop. The family phone uses the tunnel URL.

| Socket | Who connects | Server → client | Client → server |
|---|---|---|---|
| `WS /captions/{session_id}` | A's STT (inside the server), type mode, tests | nothing | `caption`, `set_elder`, `end` |
| `WS /events/{session_id}?role=elder&token=…` | C's `/elder` and `/evidence` screens on the laptop | all events (C1) | `set_elder`, `codeword_result` (C12) |
| `WS /events/{session_id}?role=family&token=…` | C's `/family` page on the phone | `alert`, `intervention`, `status`, `call_ended` only (C4) | nothing (inbound ignored) |

- Each session has **two random tokens**, one per role. A family token can't open `role=elder`.
  A wrong or expired token closes the socket with code `4401`.
- Tokens are checked on every connect and reconnect, and stop working when the session ends.
- How the screens learn `session_id` and the tokens is A's choice. Suggestion: the server prints
  `http://localhost:5173/elder?session=…&token=…` and a family URL on session start.
- The server sends one JSON event per WebSocket message.
- **Replay on connect (C6):** when a listener connects or reconnects, the server first sends that
  session's past events for that role, in order and from memory only, then live events. A family
  page that reconnects after the alert still sees it.

## A → B: `caption`

Sent for every interim and final transcript update from Deepgram.

```json
{"type": "caption", "session_id": "s1", "utterance_id": "u7", "revision": 2,
 "speaker_raw": "0", "text": "Nana it's me, I got in an accident",
 "start_s": 12.4, "end_s": 14.9, "is_final": false, "source": "live"}
```

- `utterance_id` stays the same for one spoken sentence. `revision` goes up on each interim update.
- One final per utterance. Updates that come after the final, or with an older revision, are
  ignored. A final may reuse the last interim's revision.
- `source` (C2, optional, default `"live"`): `"typed"` for lines typed in the noisy-hall
  fallback. Screens show a "typed" badge on those lines.
- A also calls the detector's `tick` every 1.0 s, even when nobody is speaking, so the meter can
  calm down.

## Server → C: `caption` (C1)

The server forwards each caption to **elder-role** listeners, unchanged, plus `t`:

```json
{"type": "caption", "session_id": "s1", "t": 15.1, "utterance_id": "u7", "revision": 2,
 "speaker_raw": "0", "text": "Nana it's me, I got in an accident",
 "start_s": 12.4, "end_s": 14.9, "is_final": false, "source": "live"}
```

- A newer revision of the same `utterance_id` replaces the line on screen.
- It's sent just before the detector's events for that caption, so `tactic_set.span` always
  points into text the screen already has.
- The distinct `speaker_raw` values seen so far are the voices C offers in "Who is the
  grandparent?".
- Family listeners never get captions.

Sample streams: `detection/fixtures/events-scam-grandson.jsonl` and `events-benign-party.jsonl`
(the versions with captions are on branch `b/caption-fixtures`).

## C → server → B: speaker confirmation

At the start of a call C shows "Who is the grandparent?" with the voices heard so far. One tap
sends this on the elder `/events` socket:

```json
{"type": "set_elder", "session_id": "s1", "speaker_raw": "0"}
```

`"speaker_raw": null` means "no speaker labels, score everyone". **Cards and family alerts stay
off until this is sent.** The meter works before it. Sending it again re-scores the call with
the new choice.

## C → server → B: `codeword_result` (C12)

After the `codeword` card, the grandparent taps whether the caller gave the right family code
word. The elder screen sends this on its `/events` socket:

```json
{"type": "codeword_result", "session_id": "s1", "ok": false}
```

- `ok: false`: the detector moves to `hangup` **at once** and sends the `hangup` intervention
  plus the `hangup` alert.
- `ok: true`: the **score-based** path to `hangup` (score ≥ 0.95 held for 20 s after the card)
  is turned off for the rest of the call. A `verification_avoidance` rule hit, meaning the caller
  dodged, still escalates to `hangup`.
- The detector ignores it unless the current card is `codeword`, and only the first one counts.
  It emits nothing for `ok: true`.
- The app still never asks for or stores the code word itself. The grandparent judges the answer.
- **Owner:** B implements it in `detection/hangup_detect/counter.py`, with a new `Detector`
  method (suggested name `codeword_result(ok, now_s)`). A routes the message into the session
  queue like `set_elder`.

## End of call (C5)

Inbound on `/captions/{session_id}`, or the server's own call-end logic:

```json
{"type": "end", "session_id": "s1"}
```

After `Detector.end`, the server sends to **all** listeners:

```json
{"type": "call_ended", "session_id": "s1", "t": 31.0}
```

The session's tokens expire at that point.

## B → C: `tactic_set`

Highlights for one utterance. Each one **replaces** what C shows for that utterance. An empty
list clears it.

```json
{"type": "tactic_set", "session_id": "s1", "t": 15.2, "seq": 31,
 "utterance_id": "u7", "revision": 2, "provisional": false,
 "evidence": [{"tactic": "secrecy", "quote": "don't tell Mom", "span": [24, 38], "source": "rule"}]}
```

- `provisional: true` means it comes from an interim caption. It highlights but never scores.
- At most one item per tactic per utterance. `span` is `[start, end)` into the caption `text`.

Tactics: `impersonation`, `urgency`, `secrecy`, `payment`, `threat`, `verification_avoidance`,
`remote_access`, `distress`.

## B → C: `risk`

```json
{"type": "risk", "session_id": "s1", "t": 15.2, "seq": 32,
 "score": 0.82, "level": "high",
 "contributions": {"rule": {"secrecy": 1.5, "payment": 2.0},
                   "llm": {"impersonation": 0.4},
                   "combos": {"secrecy+payment": 1.0}}}
```

- `score` is a 0 to 1 risk score, not a calibrated probability. Levels: `low`, `elevated`,
  `high`.
- Sent only when the score moves by at least 0.01 or the level changes.
- `contributions` values are each part's share of the score before the sigmoid.

## B → C: `intervention`

```json
{"type": "intervention", "session_id": "s1", "t": 15.2, "seq": 33,
 "kind": "codeword", "text": "This might not be who they say. Ask: what's our family code word?",
 "latched": true}
```

Kinds in order: `codeword`, then `hangup` ("Hang up. Call back on the saved number."). Before
the first card the state is `none`, but **no `none` event is ever sent** (C8). Once shown, a
card **stays** until the call ends, even if the meter drops. It's advice already given.

## B → family page: `alert`

```json
{"type": "alert", "session_id": "s1", "t": 15.3, "seq": 34,
 "alert_id": "s1:codeword", "kind": "codeword",
 "evidence": ["don't tell Mom", "gift cards", "there's no time"],
 "summary": "Caller asked for secrecy and asked for gift cards."}
```

- At most two per call (`codeword`, `hangup`).
- `evidence` holds **at most 3** quotes, strongest first (C8).
- Same `alert_id` twice means the same alert, so show it once. Replays after a reconnect (C6)
  rely on this.

## `status` (C7)

The detector sends `status` **only to report a warning**. There's no status event at the start
of a call.

```json
{"type": "status", "session_id": "s1", "t": 40.2, "seq": 51, "mode": "rules_only",
 "warning": "duplicate final ignored"}
```

- `mode`: `rules_only` or `full` (AI layer on).
- Current warnings: `"duplicate final ignored"`, `"oldest caption dropped from the rebuild store"`.

The **server** may also send `status` (no `seq`) with an optional `stt` field when captions
start or the source changes:

```json
{"type": "status", "session_id": "s1", "t": 0.0, "stt": "deepgram", "warning": null}
```

`stt`: `deepgram`, `whisper` (offline fallback, the screen shows "offline mode"), `typed` or
`none`.

## Rules for A's server

- **Tokens:** as in Transport (C3, C4). Random per session and per role, read only for family,
  expire when the session ends, checked on every connect and reconnect.
- One detector per session, used by one task at a time (queue). Captions, ticks, `set_elder`,
  `codeword_result` and `end` all go through that queue.
- The event history kept for replay (C6) lives in memory only and is dropped when the session ends.
- Don't log transcript text by default. API keys stay on the server.

## Data handling (whole team)

- The app never asks for or stores the family code word. Grandma knows it.
- Only caller text from the last 60 s goes to Groq or Gemini, and only when the AI layer is on.
- Demo and test calls use made-up names and no real account numbers.
