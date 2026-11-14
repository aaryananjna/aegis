# Hang Up event contracts

**Status: DRAFT by B (Mihir). Needs an OK from A and C before anyone builds against it as final.**

Everything between the three parts travels as JSON events over A's WebSocket.
Every event has: `type`, `session_id`, `t` (seconds since the session started, detector clock) and `seq` (per session, always increasing).

## A → B: `caption`

Sent for every interim and final transcript update from Deepgram.

```json
{"type": "caption", "session_id": "s1", "utterance_id": "u7", "revision": 2,
 "speaker_raw": "0", "text": "Nana it's me, I got in an accident",
 "start_s": 12.4, "end_s": 14.9, "is_final": false}
```

- `utterance_id` stays the same for one spoken sentence; `revision` goes up on each interim update.
- One final per utterance. Updates that come after the final, or with an older revision, are ignored.
- A also calls the detector's `tick` every 1.0 s, even when nobody is speaking (so the meter can calm down).

## C → A → B: speaker confirmation

At the start of a call C shows "Who is the grandparent?" with the voices heard so far. One tap sends:

```json
{"type": "set_elder", "session_id": "s1", "speaker_raw": "0"}
```

`"speaker_raw": null` means "no speaker labels, score everyone". **Cards and family alerts stay off until this is sent.** The meter works before it.

## B → C: `tactic_set`

Highlights for one utterance. Each one **replaces** what C shows for that utterance. An empty list clears it.

```json
{"type": "tactic_set", "session_id": "s1", "t": 15.2, "seq": 31,
 "utterance_id": "u7", "revision": 2, "provisional": false,
 "evidence": [{"tactic": "secrecy", "quote": "don't tell Mom", "span": [24, 38], "source": "rule"}]}
```

Tactics: `impersonation`, `urgency`, `secrecy`, `payment`, `threat`, `verification_avoidance`, `remote_access`, `distress`.

## B → C: `risk`

```json
{"type": "risk", "session_id": "s1", "t": 15.2, "seq": 32,
 "score": 0.82, "level": "high",
 "contributions": {"rule": {"secrecy": 1.5, "payment": 2.0},
                   "llm": {"impersonation": 0.4},
                   "combos": {"secrecy+payment": 1.0}}}
```

`score` is a 0 to 1 risk score, not a calibrated probability. Levels: `low`, `elevated`, `high`.

## B → C: `intervention`

```json
{"type": "intervention", "session_id": "s1", "t": 15.2, "seq": 33,
 "kind": "codeword", "text": "This might not be who they say. Ask: what's our family code word?",
 "latched": true}
```

Kinds in order: `none` → `codeword` → `hangup` ("Hang up. Call back on the saved number."). Once shown, a card **stays** until the call ends, even if the meter drops. It's advice already given.

## B → family page: `alert`

```json
{"type": "alert", "session_id": "s1", "t": 15.3, "seq": 34,
 "alert_id": "s1:codeword", "kind": "codeword",
 "evidence": ["don't tell Mom", "gift cards", "there's no time"],
 "summary": "Caller asked for secrecy and asked for gift cards."}
```

At most two per call (`codeword`, `hangup`). Same `alert_id` twice means the same alert; show it once.

## B → C: `status`

```json
{"type": "status", "session_id": "s1", "t": 0.0, "seq": 1, "mode": "rules_only", "warning": null}
```

`mode`: `rules_only` or `full` (AI layer on).

## Rules for A's server

- **Family page access:** each session gets a random token. It only opens that one session, is read only, expires when the session ends and is checked on every connect and reconnect.
- One detector per session, used by one task at a time (queue).
- Don't log transcript text by default. API keys stay on the server.

## Data handling (whole team)

- The app never asks for or stores the family code word. Grandma knows it.
- Only caller text from the last 60 s goes to Groq or Gemini, and only when the AI layer is on.
- Demo and test calls use made-up names and no real account numbers.
