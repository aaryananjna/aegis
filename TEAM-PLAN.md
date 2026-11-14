# Hang Up: team plan

**Read this first.** It's the single source of truth for who does what. If you're a Claude
working in this repo, also read `CLAUDE.md` and `CONTRACTS.md`.

Last updated: 2026-11-13 by Aryan (goal, demo and status gaps; see the PR).

## Goal for the hackathon

**Deadline:** 9 pm, Sat 14 Nov 2026 (local time). **Judging time:** _TBD._

**Prizes we're going for** (proposal from the original pitch; confirm in issue #1):

| Prize | What proves it |
|---|---|
| Impactful AI | The live demo, plus held-out results on staged calls |
| Accessibility | Huge live captions on every call, one calm card at a time |
| UI/UX | The `/elder` screen and the `/family` page |
| AI Security | Reads the scam, not the voice, so a perfect voice clone doesn't beat it. The AI layer can only add risk, never remove it, so a caller saying "ignore your instructions" can't talk the score down |
| Most Secure | No audio stored, no caption text logged, keys only on the server, hashed passwords, per-call family link that expires |

**Done means** (all of these by the deadline):
1. The demo below runs cleanly in a noisy room (M4).
2. The held-out results table, with counts, described as staged role-play (M3).
3. A `README.md` that says what Hang Up is, how to run it and the held-out numbers.
4. Whatever the hackathon asks for (video, form). _TBD._

## What we're building

Hang Up sits next to a grandparent's phone while it's on speaker.

1. It captions the call in huge text, which helps hard of hearing grandparents on every call.
2. It watches how the caller behaves: pretending to be family or an official, rushing,
   asking for secrecy, asking for gift cards or crypto, threats, dodging questions, asking to
   control the computer, sounding panicked.
3. When the risk gets high it shows one calm card ("Ask: what's our family code word?") and
   alerts a family member's phone with the exact words that set it off.

It never tries to tell if a voice is fake. It reads the scam, so a perfect voice clone
doesn't beat it. **No voice-clone detection, not even as a stretch goal.** It would weaken
this claim.

**The demo:** the presenter's phone rings mid pitch, the judge answers and hears the
presenter's own cloned voice asking for bail money while the presenter stands silent. Then we
turn the laptop around and Hang Up has already caught it. Right after, the "real grandson"
calls about a birthday party and the meter stays green.

Demo details that must be true:
- The judge answers **on speakerphone**, with the phone about 10 cm from the laptop mic.
  Otherwise the laptop hears nothing.
- A named teammate off stage plays the "grandson" from the soundboard of cloned clips:
  _who: TBD_. It's a live call with scripted clips, and we say so if asked.
- The presenter taps "who is the grandparent?" at the start (issue #4).
- The scam script runs **at least 30 s** and the caller **dodges the code word question**.
  In the replay of `examples/scam-grandson.call`, the code word card and first family alert
  fire at 18.7 s and the "hang up" card at 24.3 s, after the dodge.
- The family phone has the `/family` page **open before the call**. A web page can't make
  an iPhone buzz or ring (see open question 4).

## Who does what

| Role | Person | Folder | Owns |
|---|---|---|---|
| **A: server and audio** | Aryan | `server/` | Mic audio, Deepgram live captions, the FastAPI WebSocket server, sessions, family page login |
| **B: detection** | Mihir | `detection/` | Scam rules, risk score, cards and alerts, the AI layer, test harness |
| **C: screens and demo** | _claim it_ | `web/` | Grandparent screen, family phone page, demo setup (voice clone, call script, props) |

Put your name in the table in your first PR. Stay in your own folder. If you need something
from another part, open a GitHub issue (see `CLAUDE.md`).

## Stack

| Part | Choice |
|---|---|
| Server | Python, FastAPI, WebSockets |
| Live captions | Deepgram streaming with speaker labels (diarization). Backup: local faster-whisper. Not Groq Whisper: no speaker labels, not live (issue #3) |
| Scam detection | Python package in `detection/`, no dependencies. AI layer later: Groq, Gemini as backup |
| Screens | React, Vite, Tailwind. One app, two pages: `/elder` and `/family` |
| Demo voice clone | ElevenLabs, made from the presenter's own voice with consent |
| Running the demo | Server on the presenter's laptop. Family phone joins through a Cloudflare quick tunnel over a phone hotspot |
| Database | TigerDB, for user accounts (login info) |

User accounts and login info are stored in TigerDB. Passwords are stored only as hashes
(argon2 or bcrypt), never as plain text. The connection string stays in `.env`. We don't
store audio, caption text or the family code word.

## How the parts connect

```
phone on speaker → laptop mic → A: server → Deepgram captions
                                     │  caption events
                                     ▼
                                B: Detector (detection/)
                                     │  tactic_set, risk, intervention, alert events
                                     ▼
                         C: /elder screen      C: /family phone page
```

Every message between parts is defined in `CONTRACTS.md`. Change it only through a PR that
the other two OK.

## Status

| Part | Where it is |
|---|---|
| B | **Done, all on `main`:** rules for 8 scam tactics (FTC, FBI, IRS, AARP and bank phrases), risk score, cards that match the scam (code word for family callers, "don't pay, call back" for banks, the IRS or companies), alerts, `codeword_ok`, caption fixtures, replay, type mode, test harness, demo script (`detection/demo/`) and the AI layer (Groq `qwen/qwen3.8-27b`, Gemini `gemini-3.5-flash-lite` as backup; add-only, off until the grandparent tap). Rules also survive captions that drop small words (#31) and don't flag "call the number on the back of your card" (#32). 312 tests. Practice set (synthetic, 21 calls): 11/11 scams caught, 0/10 false alarms. **Left:** held-out results once A and C record the calls, and a check on real Deepgram captions. |
| A | Not started. Aryan |
| C | Not started. Role unclaimed. C can start now from the sample event files in `detection/fixtures/` |

## Tasks

### A: server and audio
1. FastAPI server with two WebSockets per call: one where captions come in and one where C's
   screens listen. `detection/examples/server_example.py` shows the pattern.
2. Deepgram streaming from the laptop mic with interim results and speaker labels. Turn each
   result into a `caption` event (see `CONTRACTS.md`).
3. One owner task per call that feeds the detector, plus a tick every second.
4. Family page link: a random token per call that only opens that call, is read only and stops
   working when the call ends.
5. Test it in a noisy room with the phone speaker about 10 cm from the mic. Done when captions
   show up less than a second behind speech.
6. Demo network: phone hotspot plus a Cloudflare quick tunnel so the family phone can connect.
7. User accounts in TigerDB: sign up, log in and log out, hashed passwords, login sessions
   that expire. Seed demo accounts with made-up names.

### B: detection (Mihir)
1. Done and merged: rules, risk score, cards, alerts, replay, type mode, test harness and
   21 synthetic practice calls.
2. Done and merged: the AI layer (Groq, Gemini as backup), with tests proving it can never
   lower the score.
3. Left: held-out results once A and C record the calls, and a check on real Deepgram
   captions once A pushes them.

### C: screens and demo
1. `/elder` screen: huge live captions, highlighted scam words, a risk meter and one card at a
   time. Build it against `detection/fixtures/events-scam-grandson.jsonl` first.
2. A "who is the grandparent?" tap at the start of each call. Cards and alerts stay off until
   it's tapped.
3. `/family` page for the phone: the alert with the quotes and a plain summary.
4. Cards stay on screen once shown, even if the meter drops.
5. Demo kit: the presenter's consented voice clone, a soundboard of clips, the call script,
   name tag props.

### A and C together: held-out test calls
Write and record about 10 staged calls (half scams, half tricky normal calls) **without
reading B's rules**. These give the only numbers we show judges. Steps:
`detection/eval/calls/heldout/README.md`.

## Milestones

Deadline is 9 pm Sat 14 Nov, so about one day. Times are a proposal; change them in a PR if
they don't work for you.

| # | By | Done when |
|---|---|---|
| M0 | Fri 13 Nov, 11 pm | Roles claimed in the table and `CONTRACTS.md` OK'd by all three |
| M1 | Sat 14 Nov, 10 am | C's screens run on the sample event files. A's server shows live captions |
| M2 | Sat 14 Nov, 2 pm | One full run: phone on speaker → captions → detector → both screens |
| M3 | Sat 14 Nov, 4 pm | Held-out calls recorded and the results table printed |
| M4 | Sat 14 Nov, 6 pm | Feature freeze. Then five clean rehearsals in a noisy room |
| Submit | Sat 14 Nov, 8:30 pm | Everything in "Done means" submitted, 30 min before the deadline |

With this little time, B's AI layer only goes in if it's working by M2. Rules alone already
catch the practice scams. Twilio texts (open question 4) are out; keep the family page open.

## Team rules

- Work on a branch, open a PR into `main`, don't push straight to `main` with code.
- Run your part's tests before every push.
- No API keys in the repo. Put them in `.env`, which is ignored.
- Test calls use made-up names and no real account numbers.
- Numbers we show judges come only from the held-out calls, with the count, described as
  staged role-play.

## Open questions

1. Who takes C? Claim it in issue #1. (A is Aryan.)
2. Exact submission deadline and judging time, and what we must submit.
3. Can each of us merge our own PR once tests pass, or does someone review first?
4. **Family phone buzz:** keep the `/family` page open on the phone (no work), or add a Twilio
   text that links to it (new event, needs a `CONTRACTS.md` change OK'd by all three)?
5. **What goes to the AI layer before the tap:** `CONTRACTS.md` says only caller text goes to
   Groq or Gemini, but before the grandparent tap (or with no speaker labels) we can't tell
   who the caller is. Proposal for B: the AI layer stays off until the tap names a
   grandparent; with no speaker labels it stays rules only.
6. Who plays the cloned "grandson" off stage in the demo?
7. Which prizes we're going for (the table in "Goal for the hackathon" is a proposal).
8. **User accounts:** who logs in (family members, the grandparent or both), and what else a
   user record holds (for example which grandparent a family member watches, and their
   phone number). Does logging in replace the per-call family link, or work alongside it?
   Replacing it changes `CONTRACTS.md`.
