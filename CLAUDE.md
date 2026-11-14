# Instructions for any Claude working in this repo

Three people build Hang Up, each with their own Claude. You work for one of them. Read this
whole file before doing anything.

## 1. Read first, every session

1. `TEAM-PLAN.md`: what we're building, who owns which role and folder, tasks, milestones.
2. `CONTRACTS.md`: the exact messages between the parts. Build to it.
3. Open issues for your role: `gh issue list --label for-A` (or `for-B`, `for-C`).
   Also `gh issue list --label for-all`.

Ask your person which role they are (A, B or C) if `TEAM-PLAN.md` doesn't say yet.

## 2. Stay in your lane

| Role | Your folder | Never edit |
|---|---|---|
| A: server and audio | `server/` | `detection/`, `web/` |
| B: detection | `detection/` | `server/`, `web/` |
| C: screens and demo | `web/` | `detection/`, `server/` |

Shared files (`TEAM-PLAN.md`, `CONTRACTS.md`, this file) change only through a PR that says
what changed, and `CONTRACTS.md` changes need an OK from the other two roles.

## 3. Talking to the other Claudes

We talk through **GitHub issues**, so every message is written down and nobody needs to be
online at the same time.

- **To ask another role for something:** open an issue labeled with their role.
  Title format: `[A→B] short ask`. Say what you need, why you need it and what you'll do meanwhile.
  ```
  gh issue create --title "[C→A] need the family page URL format" --label for-A --body "..."
  ```
- **To answer:** comment on the issue. Close it when the ask is done, with the PR link.
- **Something for everyone** (contract change, deadline, demo timing): label `for-all`.
- **Before you start work** in a session, check your role's open issues (section 1).
- Keep messages short and concrete: file names, event names, example JSON.
- Anything your person hasn't approved (a contract change, a new dependency in a shared
  part) is a proposal. Say so in the issue.

## 4. Working rules

- Branch, PR into `main`, tests green before pushing. Don't push code straight to `main`.
- PR description: what changed, how you tested it.
- No API keys or secrets in the repo. Use `.env` (gitignored).
- Test and demo calls use made-up names and no real account numbers.
- Don't log caption text by default.
- Judge-facing numbers come only from `detection/eval/calls/heldout/`, with counts, described
  as staged role-play. Never present a recording as live.
- If you're about to send anything outside the team or spend money, ask your person first.

## 5. Useful commands

```
cd detection && python -m pytest -q                                      # B's tests
python -m hangup_detect.replay examples/scam-grandson.call --elder 0     # watch a scam call
python -m hangup_detect.cli                                              # type a call yourself
python -m hangup_detect.eval --set dev                                   # practice numbers
```
(Run these inside `detection/` after `pip install -e detection`, once B's PR is merged.)
