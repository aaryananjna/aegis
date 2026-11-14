# Overnight report (C, Aaryan's Claude)

Night of 13–14 Nov 2026. All 8 tasks are done, plus one extra (#27, which B asked for in #25).
Every PR is a draft except #27, and every CI check is green.

## Do these at 8 AM

1. **Aryan (A): make `server/` talk to the screens.** This is the demo's critical path; nothing
   live works without it.
   - **What:** issue #19, which is C1, C3, C4, C5 and C6, plus B's AI step from #16.
   - **Fastest route:** copy from `tools/dev_server/aegis_dev_server.py` (#21). Every handler maps
     to a stub in the skeleton, and it has 10 passing tests.
   - **Meanwhile:** TigerDB accounts (#12, #22) don't help the demo. Suggest pausing them until
     the live call works.
   - **If `server/` isn't ready by M2 (2 pm):** demo on `tools/dev_server` with the typed
     fallback (runbook section 3).
2. **Mihir (B): review and merge contract v2.1, #27.** It has A's four additions from #1 and B's
   AI step. Then someone reviews the web stack and merges it in order:
   - **Web stack:** #17 → #18 → #23 → #24 → #26 → #29, plus CI #28 and the dev server #21.
   - **Stacked PRs:** each is based on the previous branch. Merge with "delete branch" on, and
     GitHub retargets the next one to `main`.
3. **Aaryan (C): test on a real phone through the tunnel**, by following
   `docs/DEMO-RUNBOOK.md` (#30) section 1–2.
   - **Check:** `/family` loads through `trycloudflare.com` (the Vite `allowedHosts` fix is in
     #24) and shows "Connected".
   - **Check:** the screen stays awake (wake lock), and "Call Rose" opens the dialer.
   - **Then:** one full rehearsal with `tools/dev_server` and the typed fallback.
   - **Not yet tested:** none of these were run on a phone overnight.

## Task status

| # | Task | Branch | PR / issue | State |
|---|---|---|---|---|
| 1 | `useEvents` fix into scaffold; open scaffold and `/elder` PRs | `c/web-scaffold`, `c/elder-screen` | [#17](https://github.com/aaryananjna/aegis/pull/17), [#18](https://github.com/aaryananjna/aegis/pull/18) (on #17) | done, draft |
| 2 | Issue for Aryan: C1, C3–C6 | – | [#19](https://github.com/aaryananjna/aegis/issues/19), assigned `aryannrd` | done |
| 3 | `tools/dev_server/` reference/fallback server + `POST /typed` | `c/dev-server` | [#21](https://github.com/aaryananjna/aegis/pull/21) | done, draft |
| 4b | Elder "no speaker labels" mode | `c/elder-nolabels` | [#23](https://github.com/aaryananjna/aegis/pull/23) (on #18) | done, draft |
| 4 | `/family` phone page | `c/family` | [#24](https://github.com/aaryananjna/aegis/pull/24) (on #23) | done, draft |
| 5 | `/evidence` judge page | `c/evidence` | [#26](https://github.com/aaryananjna/aegis/pull/26) (on #24) | done, draft |
| extra | Contract v2.1 PR with A's 4 additions + B's AI step (B asked in #25) | `docs/contract-v2.1` | [#27](https://github.com/aaryananjna/aegis/pull/27) | done, **ready for review** |
| 6 | CI for `web/` | `c/web-ci` | [#28](https://github.com/aaryananjna/aegis/pull/28) | done, draft, CI green |
| 7 | Accessibility pass | `c/a11y` | [#29](https://github.com/aaryananjna/aegis/pull/29) (on #26) | done, draft. No axe: Playwright isn't installed |
| 8 | `docs/DEMO-RUNBOOK.md` | `c/demo-runbook` | [#30](https://github.com/aaryananjna/aegis/pull/30) | done, draft |

## Findings worth knowing

- **Aryan's `server/` skeleton is merged (#14)** and follows v2.1 closely: `POST /sessions`
  returns elder and family URLs with one token per role, `/captions` is localhost only, and a bad
  token closes with 4401. Most endpoints still return 501. There's no `/typed` yet.
- `server/aegis_server/roles.py` `FAMILY_EVENTS` is missing `codeword_ok`. Flagged in #19, and
  also asked for by B in #16.
- **B's `examples/server_example.py` reads `set_elder` and `codeword_result` only on
  `/captions`**, and its `/events` ignores what screens send. So the screens' taps only work with
  `tools/dev_server` (or `server/` once #19 is done).
- PR #12 and #22 (TigerDB) are open while #19 isn't started.

## Verified vs not verified

| Claim | How |
|---|---|
| #17 builds; the `useEvents` StrictMode fix works | build; `send()` exercised by `/elder` live runs |
| #18 `/elder` in fixture and live mode | 9 tests; screenshots; live run: captions, interim, typed line, voice tap, "They didn't" → hangup, "They knew it" → `codeword_ok` |
| #21 dev server does C1, C3–C6, C12 and `/typed` | 10 pytest tests; real uvicorn run with `typed_cli.py` → typed captions → codeword card → alert → `call_ended` |
| #23 Start protection → `set_elder null` → real card | fixture shots; live with `tools/dev_server` and unlabeled typed lines |
| #24 `/family` at 390×844 | fixture shots (idle, amber, red + earlier); live with a real family token: alert → "They passed the code word" → "Call ended" |
| #26 `/evidence` chart, hover, breakdown, table | screenshots; 5 reducer tests; arrow keys step 18.7 → 18.0 → 15.0 s |
| #27 contract matches the code on `main` | read against `counter.py`, `events.py`, `pipeline.py`, `INTEGRATION.md` |
| #28 CI | same commands on clean exports: top of stack 20/20, scaffold build OK. **On GitHub only the skip path has run** (no `web/` on `main` yet) |
| #29 every control named, focus ring on every Tab stop, contrast ≥ 4.5 (text) / ≥ 3 (large) | Chrome DevTools accessibility tree, real Tab presses, computed WCAG contrast; re-checked after the fixes |
| #30 runbook commands | session one-liner, `/health`, typed CLI, end of call and sample URLs run tonight; `cloudflared 2026.11.0` installed |
| **Not verified** | a real tunnel and phone (vibration, wake lock, `tel:`); A's mic and Deepgram path (`server/` is a skeleton); `/evidence` showing "rules + AI" with real AI evidence (needs a key); VoiceOver; 200% zoom |

## Failures and fixes during the night

- **`send()` silently did nothing in live mode.** React StrictMode's first socket cleared the
  shared ref after the second connected. Fixed in #17 (and #18 is rebased on it).
- **Parallel headless screenshots came out ~4 s behind:** background tabs throttle timers. I
  re-took them one at a time. It's a test artifact, not an app bug.
- **#29 found five real issues**, all fixed:
  - the evidence chart had no focus ring
  - mist text was 4.49:1 on the amber band
  - "Warning" was exactly 3.00:1 on the red tint
  - voice button names changed as people talked
  - heading levels on `/family` were off

## Decisions I made without asking

- **The web PRs are stacked:** #17 ← #18 ← #23 ← #24 ← #26 ← #29, so each diff shows one feature.
  The dev server, CI, runbook and contract PRs are based on `main`.
- **Issue #19 is labelled `for-all` and `for-A`.** You asked for `for-all`; `for-A` makes it show
  up in Aryan's own list (`CLAUDE.md` §1).
- **I did #25 (B → C) before task 6.** It wasn't on your list, but it's for C, doc-only, and
  unblocks both A and B.
- **#27 is not a draft**, so B can review it as asked.
- **`tools/dev_server/` sits outside every lane** (you asked for it). It's labelled as a
  reference for A and a demo fallback, not `server/`.
- **`/family` reads `name` and `phone` from the link.** They're display only; I proposed them to
  A in #19, and they're not in the contract. Sample calls use Rose and +1 555 0100 (fictional).
- **Vite `allowedHosts: ['.trycloudflare.com']`** (#24), or the phone can't load the page through
  the tunnel.
- **Two colors changed for contrast** in #29: mist `#93a0ae`, and a text-only red `#e8675d`.
- **I installed `cloudflared`** (Homebrew), but **opened no tunnel**, so the laptop wasn't left
  on the public internet overnight.

## Screenshots

In this branch: [`docs/overnight-shots/`](overnight-shots/) (13 images, 1280×800 laptop and
390×844 phone). All are from sample calls or local test sessions, with made-up names.
