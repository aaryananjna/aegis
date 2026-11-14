# Integration audit: V1 plan vs V2 code

Branch `integration/unify-contracts` (at `c8c1637`), audited 2026-11-13. Read-only: no code,
contract or plan file was changed. Everything below was read or run unless marked
**not verified**.

> **Update after approval (2026-11-13):** `integration/unify-contracts` was fast-forwarded to
> `origin/main` (`1a3a523`) and `origin` now points to `github.com/aaryananjna/aegis.git`.
> C1–C8 plus a new C12 (`codeword_result`, which answers G7) are written into `CONTRACTS.md`
> v2.1 on branch `docs/contract-v2.1`. V1 is archived. The rest of this file is the audit as run.

V1 = branch `backup/my-original-docs` (`PROJECT.md`, `CONTRACTS.md` v1.0, `07-architecture.md`,
`tasks/*.md`, `fixtures/demo_call_events.jsonl`).
V2 = `CONTRACTS.md` on `main` plus the code in `detection/`.

## 1. Summary

- **Only B's part exists.** The repo has one package, `detection/hangup_detect` (rules, risk,
  cards, alerts, replay, type mode, eval), and an example FastAPI server. There is **no `server/`
  (A) and no `web/` (C)** on any branch. No branch has commits by A.
- **Tests are green:** 171/171 on this branch, 178/178 on `origin/b/caption-fixtures`.
- **The pipeline works end to end at the detector level.** Through B's example server over real
  WebSockets, a typed scam call reaches HIGH, then the code word card plus family alert, then the
  hang up card plus a second alert (section 6).
- **Biggest gaps for the demo:**
  1. There's no real server and no screens.
  2. Screens never receive `caption` events. The contract doesn't route them to C, and the
     example server doesn't forward them.
  3. There are no call start or end events and no first `status` event.
  4. There's no family-only event filter or token.
  5. Type mode is a terminal tool and can't drive the screens.
- **V2 is a deliberate simplification of V1.** Keep V2's envelope and names. Port a few V1 ideas
  as **additive** fields and events (section 8). No breaking change is needed for the demo.
- **Housekeeping:**
  - This branch is 5 commits behind `origin/main`. Only `TEAM-PLAN.md` changed in those commits.
  - `origin` still points to `github.com/aaryananjna/hangup.git`. The repo is now named `aegis`.
    GitHub redirects for now. Not changed.

## 2. Branch inventory

`git fetch --all --prune` on 2026-11-13. `gh` isn't installed here, so PRs and issues were
**not verified**. The issue numbers below come from `TEAM-PLAN.md`.

| Branch | Last commit | Author | Date (-0500) | Not in `origin/main` |
|---|---|---|---|---|
| `origin/main` | `1a3a523` Merge PR #6 docs/team-plan-gaps | Aryan Dubey | 11-13 23:09 | (base) |
| `origin/docs/team-plan-gaps` | `0eea1b7` Team plan: user accounts stored in TigerDB | Aryan Dubey | 11-13 23:14 | 1 commit, `TEAM-PLAN.md` only (+11/-2) |
| `origin/b/caption-fixtures` | `1961cb7` Caption events in replays and fixtures for C's screens | Mihir Kolakaluri | 11-13 23:12 | 1 commit: `replay.py` (`--captions`), both fixtures, `INTEGRATION.md`, new `tests/test_caption_fixtures.py`, `tests/test_s6_replay.py` |
| `origin/b/detection` | `6ba5751` Simplify: one evidence value and scoring path | Mihir Kolakaluri | 11-13 21:25 | none (merged as PR #2) |
| `integration/unify-contracts` (local, this) | `c8c1637` Merge PR #2 | Aryan Dubey | 11-13 21:31 | none. **Behind main by 5** (`16e5c4a`, `4908682`, `3fbfea3`, `3459404`, `1a3a523`; all `TEAM-PLAN.md`) |
| `backup/my-original-docs` (local) | `909deb9` Add sample scam call events | Aaryan Anjna | 11-13 21:29 | 2 commits (`691dcc6`, `909deb9`): V1 docs |
| `main` (local) | `909deb9` | | | stale local pointer, equals the backup branch |

**Developer A:** In `TEAM-PLAN.md` on `origin/main`, Aryan takes role A and A's status is "Not
started". No branch has server code.

**People:** Mihir is B and Aryan is A. Role C reads "_claim it_" in `TEAM-PLAN.md`. You're
taking C, so add your name in your first PR.

### Files on `origin/main`

| Kind | Files |
|---|---|
| Source | `detection/hangup_detect/{__init__,types,events,config,rules,risk,counter,pipeline,replay,cli,eval}.py`, `detection/examples/server_example.py` |
| Tests | `detection/tests/test_{s1_types,s2_rules,s3_risk,s4_counter,s5a_detector,s5b_provisional,s6_replay,s7_eval,review_fixes}.py` (+ `test_caption_fixtures.py` on `b/caption-fixtures`) |
| Fixtures and data | `detection/fixtures/events-{scam-grandson,benign-party}.jsonl`, `detection/examples/{scam-grandson,benign-party}.call`, `detection/eval/calls/dev/*.call` (8 scam + 8 benign, synthetic), `detection/eval/calls/heldout/README.md` (**no held-out calls yet**) |
| Docs | `CLAUDE.md`, `CONTRACTS.md` (V2 draft), `TEAM-PLAN.md`, `README.md` (one line: `# hangup`), `detection/INTEGRATION.md` |
| CI and config | `.github/workflows/detection.yml` (pytest on Python 3.12), `detection/pyproject.toml` (no runtime deps), `.gitignore` |

## 3. Test results

Setup: the system Python is 3.13.1 without pytest. I made a throwaway venv in the session
scratchpad (`pytest 9.2.0`, `fastapi 0.162.7`, `uvicorn`, `httpx`, `websockets`) and ran with
`PYTHONDONTWRITEBYTECODE=1 -p no:cacheprovider`, so nothing was written in the repo. Node and npm
are **not installed** on this machine, and C's React/Vite app will need them.

```
# this branch (code identical to origin/main)
cd detection && pytest -q        → 171 passed in 0.27s
# origin/b/caption-fixtures (exported with git archive to the scratchpad)
cd detection && pytest -q        → 178 passed in 0.26s
```

```
python -m hangup_detect.eval --set dev
Set: dev (synthetic, written by Claude). 8 scam + 8 benign calls.
  Caught (reached HIGH):     8/8 (100%)
  False alarms:              0/8 (0%)
  Time to HIGH from onset:   median 20.15 s, max 26.0 s (n=8)
  Time to family alert:      median 20.15 s, max 26.0 s (n=8)
  Processing per caption:    median 0.051 ms, p95 0.091 ms
--set dev --no-speakers      → same 8/8, 0/8
--set heldout                → 0 scam + 0 benign calls (N/A), exit 0
```

These are dev numbers on synthetic calls and not judge-facing (`CLAUDE.md` §4).

## 4. The contract the code actually uses

Sources: `detection/hangup_detect/events.py:5-30`, `pipeline.py`, `counter.py`, `risk.py`,
`examples/server_example.py`, plus `replay.py` on `b/caption-fixtures`.

### Transport (example server only; there's no real server)

| What | Code | Line |
|---|---|---|
| Captions in | `WS /captions/{session_id}`, JSON messages `caption`, `set_elder`, `end` | `server_example.py:103-113`, `72-94` |
| Events out | `WS /events/{session_id}`, one JSON event per message, all events to every listener | `server_example.py:116-126`, `63-69` |
| Sessions | created on first connect to either path, never cleaned up | `server_example.py:97-100` |
| Tick | every 1.0 s through the same queue | `server_example.py:58-61` |
| Family token, roles, REST, health | **none** | comment only at `server_example.py:118` |

### Envelope

Detector events have `type`, `session_id`, `t` and `seq` (`events.py:5-6`):
- `t` is seconds since the session started on the detector clock, rounded to 3 places. It never
  goes backwards (`pipeline.py:100-104`).
- `seq` is per session and starts at 1 (`pipeline.py:106-108`).

`session_id` is any string: the URL path segment, a `# id:` from a `.call` file, or `"typed"` in
the CLI. `alert_id` is `"{session_id}:{kind}"` (`events.py:25`). `utterance_id` is chosen by
whoever sends captions (`u0…` in replay, `t0…` in the CLI).

### Events

| Event | Shape in code | Notes |
|---|---|---|
| `caption` (A→B) | `utterance_id, revision, speaker_raw, text, start_s, end_s, is_final` | The parser ignores `session_id` and forces `speaker="unknown"` (`server_example.py:83-85`). Text is capped at 2000 chars, and bad times raise (`types.py:55-72`). |
| `caption` (→C) | only in fixtures on `b/caption-fixtures`: the A→B shape plus `session_id`, `t`, **no `seq`** | Not emitted by the example server. Not in `CONTRACTS.md`. |
| `set_elder` | `{"type":"set_elder","speaker_raw":"0"\|null}` | Clears all evidence and rebuilds it from stored finals (`pipeline.py:66-76`). |
| `end` (in) | `{"type":"end"}` | `server_example.py:88`. **Not in `CONTRACTS.md`.** |
| `tactic_set` | `utterance_id, revision, provisional, evidence[{tactic, quote, span, source}]` | At most one item per tactic per utterance (`rules.py:103-114`). Interims are `provisional:true` and never score (`pipeline.py:47-49`). An empty list is sent only to clear earlier highlights (`pipeline.py:118-124`). |
| `risk` | `score` (4 dp), `level`, `contributions{rule:{tactic:v}, llm:{}, combos:{"a+b":v}}` | Sent only when the score moves at least 0.01 or the level changes (`pipeline.py:134-137`). Values are logit terms, not probabilities. |
| `intervention` | `kind, text, latched` | Only `codeword` and `hangup` are ever emitted, so `latched` is always `true` (`counter.py:44-61`, `events.py:19-21`). |
| `alert` | `alert_id, kind, evidence[≤3 quotes], summary` | Two at most per call (`counter.py:60-61`). |
| `status` | `mode` is always `"rules_only"`, plus `warning` | Sent **only** for warnings: "duplicate final ignored" and "oldest caption dropped…" (`pipeline.py:42, 55, 110-111`). |

**Tactics:** `impersonation, urgency, secrecy, payment, threat, verification_avoidance,
remote_access, distress` (`types.py:12-20`).

**Risk model:**
- Score is `sigmoid(-3 + Σ rule + Σ llm + Σ combos)` (`risk.py:89-91`).
- Each piece of evidence has a 120 s half-life and is ignored after 600 s (`risk.py:44-52`).
- Per tactic, it takes the strongest hit plus half the second strongest; further repeats add
  nothing (`risk.py:54-62`).
- There are 6 combo pairs, capped at 2.0 in total (`config.py:17-20`, `risk.py:80-86`).
- Levels are `low`, `elevated` and `high`, with hysteresis: enter at 0.80 and 0.50, exit at 0.60
  and 0.35. HIGH needs live rule evidence (`risk.py:17-27`, `config.py:34-37`).

**Speaker confirmation:**
- Until `set_elder`, everyone is scored and no cards or alerts fire (`pipeline.py:138`).
- After it, `speaker_raw == elder` marks the grandparent, and their lines are never scored
  (`pipeline.py:91-93, 113-116`).

**Interim revisions:**
- Stale or equal-revision interims are dropped (`pipeline.py:43-46`).
- A final may reuse the last interim's revision (`pipeline.py:45`).
- A second final for the same utterance is ignored and produces a `status` warning
  (`pipeline.py:41-42`).

**Code word:**
- No word is stored or checked anywhere.
- After the `codeword` card, any rule hit for `verification_avoidance` ("there's no time", "just
  trust me", "stay on the line"…) escalates to `hangup` at once (`counter.py:50-51`). So does a
  score of at least 0.95 that has lasted 20 s since the card (`counter.py:52-53`).

### Where the code disagrees with V2 `CONTRACTS.md`

| # | `CONTRACTS.md` | Code | Severity |
|---|---|---|---|
| D1 | L6: "Every event has `type`, `session_id`, `t`, `seq`" | Inbound `caption`, `set_elder` and `end` have none of these. Fixture captions have `t` but no `seq`. | doc fix |
| D2 | L80: `status` at `t=0, seq=1` | No first `status`. The first event is `risk` with `seq 1`. `status` appears only with a warning. | doc fix or add |
| D3 | L83: `mode` is `rules_only\|full` | Always `rules_only`, because there's no AI layer | expected for now |
| D4 | L64: kinds are `none` → `codeword` → `hangup` | `none` is never emitted | doc fix |
| D5 | (missing) how captions reach C | C needs them for huge captions and for the "who is the grandparent" voice list. The example server doesn't forward them. | **gap** |
| D6 | (missing) `end` message, call ended event | `server_example.py` accepts `end`. No event tells screens the call ended. | **gap** |
| D7 | L5: "over A's WebSocket", no paths | `/captions/{sid}` and `/events/{sid}` in the example | doc gap |
| D8 | L87: family token, read only, expires | Not implemented (no server). The example sends all events, including tactic quotes, to every listener. | **gap (A)** |
| D9 | L75: alert `evidence` list | Capped at 3 quotes (`counter.py:61`) | doc fix |
| D10 | L27: `set_elder` has `session_id` | Ignored; the session comes from the URL | harmless |
| D11 | (missing) status warnings | "duplicate final ignored" and "oldest caption dropped from the rebuild store" | doc fix |

## 5. V1 vs V2 comparison

| Feature | V1 (`backup/my-original-docs`) | V2 (code) | Status | Recommendation | Reason |
|---|---|---|---|---|---|
| Envelope | `call_id, seq, t_ms, payload{}` | flat fields, `session_id, t` (s), `seq` | intentionally different | keep V2 | All code, tests and fixtures use V2. Changing it is breaking for no gain. |
| Enums | UPPERCASE; levels LOW/CAUTION/HIGH | lowercase; low/elevated/high | intentionally different | keep V2 | same reason |
| Tactics | 8, with family and authority impersonation split, plus `SENSITIVE_REQUEST` | 8: one `impersonation`, adds `remote_access` and `distress`, no `sensitive_request` | intentionally different | keep V2; maybe add `sensitive_request` later (B) | V2 covers tech-support scams. Asks for an SSN or PIN aren't covered (**not verified** on dev calls). |
| Tactic event | one `tactic` per evidence with `evidence_id`, `strength`, `explanation` | `tactic_set` per utterance with `span`, replaceable | intentionally different | keep V2 | Spans and replacement handle interim revisions. V1 had no story for that. |
| Plain-words explanation per tactic | `explanation` field | only in the alert `summary` (`counter.py:18-35`) | partial | C maps tactic to label in the UI | no contract change needed |
| (a) LLM quote guard and drop count | required | no LLM code at all | missing | port with the LLM layer (B) | `risk.py` already keeps rule and LLM evidence apart, and tests prove the LLM can't lower the score (`test_s3_risk.py:79-158`) |
| (b) Contributions and combos for the evidence dashboard | `contributions[]`, `combos[]` | `contributions{rule,llm,combos}` | implemented | keep V2 | Dict by source is richer. C can render it directly. |
| (c) Time decay, no repeat inflation | exp decay τ=120 s, max per tactic | half-life 120 s, best plus half the second, 600 s horizon | implemented | keep V2 | `test_ten_urgency_repeats_stay_low`, `test_decay_half_life` |
| (d) LLM fallback Groq → Gemini → rules, status | yes | none; `status.mode` stuck on `rules_only` | missing | defer (TEAM-PLAN: only if working by M2) | Rules alone catch the dev set |
| (e) STT fallback Deepgram → Whisper, "offline mode" | yes | no STT code | missing | A; add optional `status.stt` (additive) | No server yet |
| (f) Metrics (STT, detection, LLM latency) | `metrics` event | eval prints per-caption ms; no event | partial | defer; keep it in eval output | Not needed for the demo |
| (g) Type mode / inject-text | `POST /api/inject-text` drives the real pipeline and screens | `python -m hangup_detect.cli` (stdin, terminal only). Replay. The example server takes caption JSON over WS. | partial | port as a small typed-caption path in A's server, plus optional `caption.source:"typed"` | The demo fallback for a noisy hall must reach the screens and be labeled honestly |
| (h) Eval harness | tricky benign, FA rate, time to alert, cross-validated fitted weights | tricky benign (surprise party, bank fraud alert, pharmacy, friend in a hurry…), FA rate, time to HIGH and alert, group leak guard; **no fitted weights** | partial | keep; drop CV weights | Too little data to fit honestly. Held-out set is empty (needs A and C). |
| (i) Audio never written to disk | must verify | no audio code exists; the only `open()` is a read (`replay.py:151`); logs never include text (`server_example.py:91`) | trivially true | re-check on A's server | |
| (j) Code word | stored as a salted hash; VERIFIED when heard; HANG_UP on dodge or wrong word | nothing stored; no VERIFIED; dodge is any `verification_avoidance` rule hit after the card | intentionally different, with one gap | keep "never stored". Defer VERIFIED. | See gap G7: a correct answer still ends in `hangup` 20 s later if the score stays ≥ 0.95 |
| CAUTION card | yes, at 0.5 | no; only the meter goes `elevated` | intentionally different | keep V2 | "One calm card at a time" |
| `call_started` / `call_ended` | yes | none | missing | port as additive events (A emits) | C needs a lifecycle, and the family page needs to know the call ended |
| Family role filter | `?role=family` gets only lifecycle, alert and intervention events | none | missing | port (additive), plus a token (A) | privacy and the "Most Secure" prize |
| Health and REST, vault, contacts | `/api/health`, `/api/calls`, `/api/vault` | none | missing | drop the vault and contacts. Health is optional (A). | V2 never stores the code word. The card says "saved number" with no contact data. |
| Speaker labels | none in MVP | Deepgram diarization plus the C tap (`set_elder`) | intentionally different | keep V2 | stronger protection against Grandma's own words |
| Fixture | `fixtures/demo_call_events.jsonl` (V1 shape) | `detection/fixtures/*.jsonl` (V2 shape; captions only on `b/caption-fixtures`) | V2 replaces V1 | use V2 fixtures and drop the V1 one | V1 shapes match no code |

## 6. End to end

There's **one** runnable server, B's `detection/examples/server_example.py`, documented as "not
production code". A's server doesn't exist, so nothing is duplicated yet. Nothing connects STT
or real audio.

What I ran:
1. `uvicorn server_example:app --port 8765`
2. A WebSocket client (scratchpad `e2e_client.py`, not committed):
   1. Subscribed to `/events/e2e1`.
   2. On `/captions/e2e1`, sent `set_elder "0"`, then the 8 lines of
      `examples/scam-grandson.call`, each as an interim (rev 0, first half of the text) and then a
      final (rev 1).
   3. Sent one malformed caption, then `end`.

Result: 15 events. All events are shown, so the stream is shorter than 30.

```
{"type":"risk","t":0.002,"seq":1,"score":0.0474,"level":"low",...}
{"type":"tactic_set","t":0.753,"seq":2,"utterance_id":"u1","revision":0,"provisional":true,"evidence":[impersonation "it's me"]}
{"type":"tactic_set","t":0.905,"seq":3,"utterance_id":"u1","revision":1,"provisional":false,"evidence":[impersonation "it's me", distress "I got in an accident"]}
{"type":"risk","t":0.905,"seq":4,"score":0.2315,"level":"low"}
{"type":"tactic_set","t":2.411,"seq":5,"utterance_id":"u3","revision":1,"provisional":false,"evidence":[secrecy "Please don't tell Mom"]}
{"type":"risk","t":2.411,"seq":6,"score":0.7817,"level":"elevated", combos impersonation+secrecy 0.99}
{"type":"tactic_set","t":3.768,"seq":7,"utterance_id":"u5","revision":0,"provisional":true,"evidence":[urgency "right now", payment "bail money"]}
{"type":"tactic_set","t":3.92,"seq":8,"utterance_id":"u5","revision":1,"provisional":false,"evidence":[urgency "right now", payment "bail money"]}
{"type":"risk","t":3.92,"seq":9,"score":0.9937,"level":"high", ...4 combos}
{"type":"intervention","t":3.92,"seq":10,"kind":"codeword","text":"This might not be who they say. Ask: what's our family code word?","latched":true}
{"type":"alert","t":3.92,"seq":11,"alert_id":"e2e1:codeword","evidence":["bail money","Please don't tell Mom","it's me"],"summary":"Caller claimed to be someone you know or an official, rushed the call, ..."}
{"type":"tactic_set","t":5.275,"seq":12,"utterance_id":"u7","revision":0,"provisional":true,"evidence":[urgency "no time", verification_avoidance "there's no time"]}
{"type":"tactic_set","t":5.426,"seq":13,"utterance_id":"u7","revision":1,"provisional":false,...}
{"type":"intervention","t":5.426,"seq":14,"kind":"hangup","text":"Hang up. Call back on the saved number.","latched":true}
{"type":"alert","t":5.426,"seq":15,"alert_id":"e2e1:hangup","evidence":["there's no time","bail money","Please don't tell Mom"],...}
server log: "bad caption message skipped: KeyError"   (no caption text logged)
```

So **typed transcript → detection → risk → intervention → family alert works today** through
the example server. What's missing:
- No `caption` events reached the listener.
- Nothing marked the call as ended. `end` produced no event, because the score barely moved.
- There was no role or token separation.

Also run:
- `replay examples/scam-grandson.call --elder 0` gives the code word card at 18.7 s and the hang
  up card at 24.3 s, matching `TEAM-PLAN.md`.
- `replay examples/benign-party.call --elder 0` produces only the starting `risk` event (green).
- `cli` with typed lines gives the same card sequence.

**Code word check:** caller says "Pancakes. It's pancakes, Nana", grandma says "Okay, that's
right", and there's no dodge. The `hangup` card and a second alert still fire at 26 s, 20 s after
the `codeword` card at 6 s, because the score stays ≥ 0.95. Recorded as G7.

## 7. Frontend

There's **no frontend code** on any branch: no `web/`, no `package.json`. Node isn't installed on
this laptop.

C should build against:
- **Event shapes:** V2 `CONTRACTS.md` (B→C sections) plus the additive changes in section 8.
- **Fixtures:** `detection/fixtures/events-scam-grandson.jsonl` and `events-benign-party.jsonl`
  **from `origin/b/caption-fixtures`**. Those include `caption` events. The `main` versions don't,
  so an `/elder` screen can't show captions from them.
- **Not the V1 fixture** `fixtures/demo_call_events.jsonl`. Its shape matches no code.
- **For a live socket before A's server exists:** run `server_example.py` and send captions to
  `/captions/{sid}`. It won't forward captions to the screen (D5).

C needs from the stream:
- captions, with interim revisions replacing the line by `utterance_id`
- `tactic_set` spans to highlight, keyed by `utterance_id`
- `risk.level` for the meter (no percentages on the elder screen)
- one latched `intervention` card
- `alert` with `alert_id` dedupe for `/family`
- the distinct `speaker_raw` values seen so far, for the "who is the grandparent?" tap that sends
  `set_elder`

## 8. Gaps ranked by demo impact

| # | Gap | Owner | Impact |
|---|---|---|---|
| G1 | No real server: no Deepgram, sessions, or token | A | Blocks M2. The example server is a stopgap. |
| G2 | No `/elder` or `/family` screens; Node not installed | C | Blocks M1 for C |
| G3 | Captions aren't forwarded to screens (D5); fixtures with captions not merged | A, B | No huge captions, and no voice list for the tap |
| G4 | No way for C's screen to send `set_elder`; the example only reads it on `/captions` | A | Cards and alerts never fire without it |
| G5 | No call lifecycle (`call_ended`) and no first `status`; late joiners and reconnects miss past events | A | The family page opened before the call works. A reconnect after the alert misses it. |
| G6 | No family filter or token (D8) | A | Privacy claim and the Most Secure prize |
| G7 | No VERIFIED: a correct code word still leads to `hangup` after 20 s if the score stays ≥ 0.95 | B (decision for all) | Not hit by the scripted demo (the caller dodges). Risky if a judge tries "the right answer". |
| G8 | Type mode can't drive the screens | A, C | Noisy-hall fallback |
| G9 | Held-out set empty | A, C | No judge-facing numbers (M3) |
| G10 | No LLM layer, metrics or STT fallback | B, A | Deferred by plan |
| G11 | Repo renamed to `aegis`; `origin` still `hangup.git`; `README.md` is one line | all | Low; GitHub redirects for now |
| G12 | `docs/team-plan-gaps` adds TigerDB accounts, against "no database" in the merged plan | all | Scope risk one day before the deadline. Open question 8. |

## 9. Proposed `CONTRACTS.md` changes

These are proposals and need an OK from A and B. All of them are additive except C10 and C11,
which I don't recommend for now.

| # | Change | Type | Files it would touch |
|---|---|---|---|
| C1 | **Server forwards every `caption` to `/events` listeners** (elder role only). Same fields as A→B plus `session_id` and `t`, **no `seq`** (`seq` orders B's events). This matches `b/caption-fixtures`. | ADDITIVE | `CONTRACTS.md`, `server/` (A), merge `b/caption-fixtures` (B) |
| C2 | Optional `caption.source: "live" \| "typed"`, so typed fallback lines show a "typed" badge | ADDITIVE | `CONTRACTS.md`, `server/`, `web/` |
| C3 | Write down the transport: `WS /captions/{session_id}` (server-internal or STT in), `WS /events/{session_id}?role=elder\|family&token=…` (out). The elder screen sends `set_elder` as JSON on its `/events` socket (or A picks a REST route; A decides). | ADDITIVE | `CONTRACTS.md`, `server/`, `web/` |
| C4 | `role=family` receives only `alert`, `intervention`, `status` and `call_ended`. No captions or `tactic_set`. Token checked on every connect. | ADDITIVE | `CONTRACTS.md`, `server/` |
| C5 | `call_ended` event `{type, session_id, t, seq?}` emitted by the server after `Detector.end`. Document the inbound `end` message. | ADDITIVE | `CONTRACTS.md`, `server/`, `web/` |
| C6 | On (re)connect, the server replays that session's past events for the role, from memory only | ADDITIVE | `CONTRACTS.md`, `server/` |
| C7 | `status`: document that the detector emits it only for warnings. Add optional `stt: "deepgram"\|"whisper"\|"typed"\|"none"` emitted by the server. Drop the "t=0, seq=1" example. | ADDITIVE (doc fix) | `CONTRACTS.md`, `server/` |
| C8 | Doc fixes for D1, D4, D9 and D11: envelope sentence applies to B's events; `none` is never sent; alert evidence ≤ 3 quotes; list the warning strings | ADDITIVE (doc only) | `CONTRACTS.md` |
| C9 | Later, with the LLM layer: `status.mode:"full"`, optional `status.llm_dropped_quotes` (V1 quote guard counter) | ADDITIVE | `CONTRACTS.md`, `detection/` |
| C12 | **Inbound `codeword_result` `{"ok": true\|false}`** sent by the elder screen on its `/events` socket after the `codeword` card. `ok:false` triggers `hangup` and its alert at once. `ok:true` turns off the score-based `hangup` path (a `verification_avoidance` rule hit still escalates). Fixes G7 without a `verified` card. Owner B (`counter.py`). A routes it. | ADDITIVE | `CONTRACTS.md`, `detection/hangup_detect/{counter,pipeline}.py` (B), `server/` (A), `web/` (C) |
| C10 | V1 envelope (`call_id`, `t_ms`, `payload`), UPPERCASE enums, V1 REST and vault | BREAKING | **Drop.** Nothing uses them. |
| C11 | A `verified` intervention that can follow `codeword` (V1 VERIFIED) | BREAKING (changes "cards never go backwards" and latching) | **Defer.** If G7 matters, a smaller ADDITIVE option is a `hangup_score` delay change in `detection/config.py`, which is B's call. |

## 10. Next steps (approved)

1. Done: fast-forwarded `integration/unify-contracts` and repointed `origin` at `aegis`.
2. `CONTRACTS.md` v2.1 (C1–C8, C12) on branch `docs/contract-v2.1`, waiting for A and B to OK it.
   The issue text is in `docs/ISSUE-contract-v2.1.md`.
3. Waiting on B: merge `b/caption-fixtures` and implement C12.
4. C: scaffold `web/` on branch `c/web-scaffold` against the caption fixtures.
