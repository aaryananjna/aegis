# Hang Up: team plan

**Read this first.** It's the single source of truth for who does what. If you're a Claude
working in this repo, also read `CLAUDE.md` and `CONTRACTS.md`.

Last updated: 2026-11-13 by Mihir (B).

## What we're building

Hang Up sits next to a grandparent's phone while it's on speaker.

1. It captions the call in huge text, which helps hard of hearing grandparents on every call.
2. It watches how the caller behaves: pretending to be family or an official, rushing,
   asking for secrecy, asking for gift cards or crypto, threats, dodging questions, asking to
   control the computer, sounding panicked.
3. When the risk gets high it shows one calm card ("Ask: what's our family code word?") and
   alerts a family member's phone with the exact words that set it off.

It never tries to tell if a voice is fake. It reads the scam, so a perfect voice clone
doesn't beat it.

**The demo:** the presenter's phone rings mid pitch, the judge answers and hears the
presenter's own cloned voice asking for bail money while the presenter stands silent. Then we
turn the laptop around and Hang Up has already caught it. Right after, the "real grandson"
calls about a birthday party and the meter stays green.

## Who does what

| Role | Person | Folder | Owns |
|---|---|---|---|
| **A: server and audio** | _claim it_ | `server/` | Mic audio, Deepgram live captions, the FastAPI WebSocket server, sessions, family page login |
| **B: detection** | Mihir | `detection/` | Scam rules, risk score, cards and alerts, the AI layer, test harness |
| **C: screens and demo** | _claim it_ | `web/` | Grandparent screen, family phone page, demo setup (voice clone, call script, props) |

Put your name in the table in your first PR. Stay in your own folder. If you need something
from another part, open a GitHub issue (see `CLAUDE.md`).

## Stack

| Part | Choice |
|---|---|
| Server | Python, FastAPI, WebSockets |
| Live captions | Deepgram streaming with speaker labels (diarization). Backup: local faster-whisper |
| Scam detection | Python package in `detection/`, no dependencies. AI layer later: Groq, Gemini as backup |
| Screens | React, Vite, Tailwind. One app, two pages: `/elder` and `/family` |
| Demo voice clone | ElevenLabs, made from the presenter's own voice with consent |
| Running the demo | Server on the presenter's laptop. Family phone joins through a Cloudflare quick tunnel over a phone hotspot |

No database and no logins beyond the family page link. We don't store audio.

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
| B | Rules, risk score, cards, alerts, replay, type mode and test harness are built with 162 tests on branch `b/detection`. PR coming. Works on typed or replayed calls today. |
| A | Not started as far as B knows |
| C | Not started as far as B knows. C can start now from the sample event files in `detection/fixtures/` once B's PR is merged |

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

### B: detection (Mihir)
1. Done on the branch: rules, risk score, cards, alerts, replay, type mode, test harness and
   16 synthetic practice calls.
2. Next: code review and PR, then the AI layer (Groq), then held-out results.

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

The submission deadline is unknown to B. Whoever finds it, put it here.

| # | Done when |
|---|---|
| M0 | Roles claimed in the table and `CONTRACTS.md` OK'd by all three |
| M1 | C's screens run on the sample event files. A's server shows live captions |
| M2 | One full run: phone on speaker → captions → detector → both screens |
| M3 | Held-out calls recorded and the results table printed |
| M4 | Five clean rehearsals of the demo in a noisy room. Feature freeze |

## Team rules

- Work on a branch, open a PR into `main`, don't push straight to `main` with code.
- Run your part's tests before every push.
- No API keys in the repo. Put them in `.env`, which is ignored.
- Test calls use made-up names and no real account numbers.
- Numbers we show judges come only from the held-out calls, with the count, described as
  staged role-play.

## Open questions

1. Who takes A and who takes C?
2. Exact submission deadline and judging time.
3. Can each of us merge our own PR once tests pass, or does someone review first?
