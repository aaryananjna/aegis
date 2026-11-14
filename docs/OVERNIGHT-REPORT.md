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
| 4b | Elder "no speaker labels" mode | | | |
| 4 | `/family` phone page | | | |
| 5 | `/evidence` judge page | | | |
| 6 | CI for `web/` | | | |
| 7 | Accessibility pass | | | |
| 8 | `docs/DEMO-RUNBOOK.md` | | | |

## Findings worth knowing

- **Aryan's `server/` skeleton is merged (#14)** and follows v2.1 closely: `POST /sessions`
  returns elder and family URLs with one token per role, `/captions` is localhost only, and a bad
  token closes with 4401. Most endpoints still return 501.
- `server/aegis_server/roles.py` `FAMILY_EVENTS` is missing `codeword_ok` (B named it in #9).
  Flagged in #19.
- `CONTRACTS.md` on `main` is still v2. v2.1 (on `docs/contract-v2.1`) hasn't been OK'd or
  merged, but A and B are both building to it.
- PR #12 (TigerDB accounts) is still open.

## Verified vs not verified

| Claim | How |
|---|---|
| #17 builds | `npm run build` after the fix |
| #18 `/elder` works in fixture and live mode | see #18: build, 9 tests, headless Chrome screenshots, live run against a v2.1 test server |
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

## Screenshots

`/private/tmp/claude-501/-Users-aaryananjna-hangup-integration/856fb032-c1fb-4ed4-acfc-237c46d92ab5/scratchpad/shots/`
(on Aaryan's laptop, not in git).
