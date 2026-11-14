# Issue text (paste into GitHub)

**Title:** `[C→all] OK contracts v2.1 + three decisions before M1`
**Label:** `for-all`

---

I'm Aaryan, taking **role C** (screens and demo). I audited what's in the repo against the
original plan. The full write-up is `docs/INTEGRATION_AUDIT.md` on branch `docs/contract-v2.1`:
https://github.com/aaryananjna/aegis/compare/main...docs/contract-v2.1

**Short version:**
- B's detector is solid: 171 tests pass, and the dev set catches 8/8 scams with 0/8 false
  alarms (synthetic, not judge-facing).
- I ran a typed scam call through `detection/examples/server_example.py` over real WebSockets.
  It reached the code word card, the family alert and the hang up card.
- There's no `server/` or `web/` yet.

## Decisions needed (please reply with OK, or say what to change)

### 1. Approve `CONTRACTS.md` v2.1 (A and B)

All changes are **additive**, so nothing that works today breaks. Details are in the
"What changed in v2.1" table at the top of `CONTRACTS.md` on the branch.

| # | Change | Who builds it |
|---|---|---|
| C1 | Server forwards every `caption` to elder-role screens (`t`, no `seq`), just before the detector's events for it. This matches B's `b/caption-fixtures`. | A |
| C2 | Optional `caption.source: "live" \| "typed"` for the noisy-hall fallback | A, C |
| C3 | Sockets: `WS /captions/{session_id}` in; `WS /events/{session_id}?role=elder\|family&token=…` out. The elder screen sends `set_elder` and `codeword_result` on its `/events` socket. One token per role, close code `4401`. | A, C |
| C4 | `role=family` gets only `alert`, `intervention`, `status`, `call_ended` | A |
| C5 | Inbound `{"type":"end"}`, then the server sends `{"type":"call_ended","session_id","t"}` | A, C |
| C6 | On connect or reconnect, the server replays the session's past events for that role (memory only) | A |
| C7 | `status` is warnings only from the detector; the server may add `stt: deepgram\|whisper\|typed\|none` | A, C |
| C8 | Doc fixes: the envelope covers B's events only, `none` is never sent, alerts carry ≤ 3 quotes, warning strings listed | none |
| C12 | **New:** after the `codeword` card the elder screen sends `{"type":"codeword_result","ok":true\|false}`. `ok:false` means `hangup` plus its alert at once. `ok:true` turns off the score-based `hangup` path, but a dodge (`verification_avoidance` hit) still escalates. | **B** (`counter.py`), A routes it, C sends it |

Why C12: today, if the caller gives the **right** code word and doesn't dodge, the hang up card
still fires 20 s after the code word card, because the score stays ≥ 0.95. I tested this with
the example call plus "Pancakes. It's pancakes, Nana." A judge trying "the right answer" would
see it.

### 2. Cut TigerDB user accounts from `docs/team-plan-gaps` (all)

Proposal: **don't merge** the TigerDB commit (`0eea1b7`). Reasons:
- The deadline is 9 pm Sat.
- The merged plan says "no database and no logins beyond the family page link".
- Accounts add password storage to our Most Secure story without helping the demo.

The per-session family token (C3, C4) covers the family page. We can revisit after the
hackathon.

### 3. A starts `server/` from `detection/examples/server_example.py` (A)

Proposal: copy the example's one-owner-queue pattern into `server/`, then add, in order:
1. C1, C3, C4, C5 and C6, so C's screens can connect.
2. Deepgram streaming.
3. The tokens and the tunnel.

The example already works end to end with typed captions.

## Next task per owner

- **A (Aryan):**
  1. Create `server/` from the example with the v2.1 sockets (C1, C3–C6).
  2. Print the elder and family URLs with tokens on session start.
  3. Then Deepgram (TEAM-PLAN A tasks 2–6).
- **B (Mihir):**
  1. Merge `b/caption-fixtures`. C's screens are built on those fixtures.
  2. Implement C12 in `counter.py` with tests.
  3. Then the AI layer, if it works by M2.
- **C (Aaryan):**
  1. Scaffold `web/` (Vite, React, TS, Tailwind) on branch `c/web-scaffold`, with a
     `useEvents()` hook that reads the live socket or replays a fixture.
  2. Then the `/elder` screen, the "who is the grandparent?" tap, `/family`, and the demo kit.
- **A and C:** write and record the held-out calls without reading `rules.py`
  (`detection/eval/calls/heldout/README.md`).

Until A's server exists, C builds against the fixtures and B's example server.
