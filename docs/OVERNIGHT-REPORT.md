# Overnight report (C, Aaryan's Claude)

Night of 13–14 Nov 2026. Updated after every task. Newest status first.

## Do these at 8 AM

_Filled in as the night goes on._

## Task status

| # | Task | Branch | PR / issue | State |
|---|---|---|---|---|
| 1 | `useEvents` fix into scaffold; open scaffold and `/elder` PRs | `c/web-scaffold`, `c/elder-screen` | [#17](https://github.com/aaryananjna/aegis/pull/17), [#18](https://github.com/aaryananjna/aegis/pull/18) (stacked on #17) | done, draft |
| 2 | Issue for Aryan: C1, C3–C6 | – | [#19](https://github.com/aaryananjna/aegis/issues/19), assigned `aryannrd` | done |
| 3 | `tools/dev_server/` reference server + `POST /typed` | `c/dev-server` | [#21](https://github.com/aaryananjna/aegis/pull/21) | done, draft |
| 4b | Elder "no speaker labels" mode | `c/elder-nolabels` | [#23](https://github.com/aaryananjna/aegis/pull/23) (stacked on #18) | done, draft |
| 4 | `/family` phone page | `c/family` | [#24](https://github.com/aaryananjna/aegis/pull/24) (stacked on #23) | done, draft |
| 5 | `/evidence` judge page | `c/evidence` | [#26](https://github.com/aaryananjna/aegis/pull/26) (stacked on #24) | done, draft |
| extra | Contract v2.1 PR with A's 4 additions + B's AI step (B asked in #25) | `docs/contract-v2.1` | [#27](https://github.com/aaryananjna/aegis/pull/27), **ready for review** (not draft: B asked to review it) | done |
| 6 | CI for `web/` | `c/web-ci` | [#28](https://github.com/aaryananjna/aegis/pull/28) | done, draft, CI green |
| 7 | Accessibility pass | `c/a11y` | [#29](https://github.com/aaryananjna/aegis/pull/29) (stacked on #26) | done, draft. No axe: Playwright isn't installed |
| 8 | `docs/DEMO-RUNBOOK.md` | | | |

## Findings worth knowing

- **Aryan's `server/` skeleton is merged (#14)** and follows v2.1 closely: `POST /sessions`
  returns elder and family URLs with one token per role, `/captions` is localhost only, and a bad
  token closes with 4401. Most endpoints still return 501.
- `server/aegis_server/roles.py` `FAMILY_EVENTS` is missing `codeword_ok` (B named it in #9).
  Flagged in #19.
- `CONTRACTS.md` on `main` is still v2. v2.1 (on `docs/contract-v2.1`) hasn't been OK'd or
  merged, but A and B are both building to it.
- PR #12 (TigerDB accounts) is still open, and **Aryan's newest PR, #22, is TigerDB schema work**,
  while #19 (what the screens need from `server/` for the demo) is still open.

## Verified vs not verified

| Claim | How |
|---|---|
| #17 builds | `npm run build` after the fix |
| #18 `/elder` works in fixture and live mode | see #18: build, 9 tests, headless Chrome screenshots, live run against a v2.1 test server |
| #23 Start protection → `set_elder null` → real card | fixture screenshots (`nolabels-1-start`, `-2-auto-started`, `-3-codeword`); live with `tools/dev_server` (`live-nolabels-card`) |
| #24 `/family` at 390×844: idle, amber, red, earlier, passed code word, call ended | fixture shots `family-1-idle`, `-2-codeword`, `-3-hangup-full`; live with a real family token, `family-live-ended` |
| #26 `/evidence`: chart, hover, breakdown, table | screenshots `evidence-1-scam`, `-2-hover`, `-3-bank`; reducer tests |
| `/evidence` with real AI evidence ("rules + AI") | **not verified**: needs an API key; covered by reducer test only |
| #28 CI: `npm ci` → build → test | same commands on clean exports: `c/evidence` 20/20, `c/web-scaffold` build OK + test skipped. **On GitHub only the skip path has run** (no `web/` on `main` yet) |
| #29 every control named, rings on every Tab stop, contrast ≥ 4.5 (text) / ≥ 3 (large) | Chrome DevTools accessibility tree, real Tab presses, computed WCAG contrast; re-checked after fixes |
| Screen reader (VoiceOver), 200% zoom | **not verified** |
| Vibration, wake lock, `tel:` on a real phone | **not verified**, needs a phone |
| #21 dev server does C1, C3–C6, C12 and `/typed` | 10 pytest tests; real uvicorn run with `typed_cli.py` → typed captions → codeword card → alert → `call_ended` |

## Decisions I made without asking

- **#18 is stacked on #17** (base `c/web-scaffold`), so its diff only shows `/elder`.
- **Issue #19 is labelled `for-all` and `for-A`.** You asked for `for-all`; `for-A` makes it show
  up in Aryan's own list (`CLAUDE.md` §1).
- **`tools/dev_server/` sits outside every lane** (you asked for it). Its README and PR say plainly
  that it's a reference for A and a demo fallback, not `server/`.
- **The dev server's URLs add `name` and `phone` to the family link only**, as display fields for
  `/family` ("Watching over Rose", "Call Rose"). They're not in the contract; I proposed them to
  A in #19.

- **I did #25 (B → C: open the v2.1 contract PR) before task 6.** It wasn't on your list, but
  it's labelled for C, it unblocks A and B, and it's doc-only. #27 is not a draft, so B can
  review it.
- **`/family` takes `name` and `phone` from the link**, defaulting to "your family member" and no
  call button when they're missing. Sample calls default to Rose and +1 555 0100 (a fictional
  number).
- **I added Vite `allowedHosts: ['.trycloudflare.com']`** in #24. The tunnel plan in TEAM-PLAN
  needs it.

## Screenshots

`/private/tmp/claude-501/-Users-aaryananjna-hangup-integration/856fb032-c1fb-4ed4-acfc-237c46d92ab5/scratchpad/shots/`
(on Aaryan's laptop, not in git).
