# Aegis

Aegis listens to a phone call on speaker and warns an older adult on their laptop screen while
the scammer is still talking. It catches what the caller **says** instead of how they sound and a
cloned voice doesn't get past it. A family member's phone gets the same alert with the caller's
own words.

Built at HackUMass XIV (Nov 13 to 15, 2026) by Aryan Dubey (server and audio), Mihir
Kolakaluri (detection) and Aaryan Anjna (screens and demo).

## One call, with Aegis

Dorothy is 81 and when her phone rings she puts it on speaker next to her laptop like she
always does. Aegis shows every word of the call in big letters on the screen.

> "Hi, this is Oakbridge Bank fraud prevention about a pending wire."

It sounds official and the screen stays calm. Aegis notes the bank claim and waits.

> "Someone in Miami just tried to send $900 from your checking account."

Now there are two warning signs together, someone claiming to be the bank plus a scare about
her money. The screen turns amber and says **Be careful** with the words that worried it
highlighted.

> "I can stop it, but you have to initiate a reverse transfer yourself."

A bank never asks you to move money to undo fraud. The screen turns deep red and says
**Warning** with one calm instruction.

**This might be a scam. Don't pay or share any numbers. Ask for their name and say you'll call
back.**

At the same moment her son's phone shows the alert with the caller's own words and a button to
call his mom. When the caller pushes back with "there's no time, just do it now", the card
changes to **Hang up. Call the number on your card or their official website.**

Dorothy hangs up. Nothing was paid and nothing was shared.

That call is a staged rehearsal with invented names. Every step above is what the detector
actually does with those exact lines.

## What it does on a call

1. The laptop mic hears the call on speakerphone and Deepgram turns it into live captions.
2. The detector scores every line for 8 scam tactics: pretending to be someone, rushing,
   secrecy, unusual payment, threats, dodging questions, remote control of a device and
   sounding panicked.
3. The grandparent's screen shows huge captions with the risky words highlighted. It moves
   from **Normal call** to **Be careful** (solid amber) to **Warning** (solid deep red).
4. When a scam is likely, one card appears:
   - the caller claims to be family: **"This might not be who they say. Ask: what's our family
     code word?"**
   - a bank, the government or a company: **"This might be a scam. Don't pay or share any
     numbers. Ask for their name and say you'll call back."**
   - it keeps going: **"Hang up."** with the right number to call back
5. The family member's phone gets the same alert with up to three of the caller's exact words
   and a button to call back. It also shows "code word passed" if the caller got it right.
6. Family members can log in to see past calls with when they happened and how risky they
   looked. The grandparent never logs in because their laptop is paired once.

## How detection works

- **Rules** catch known scam wording in about 0.2 ms per caption and point at the exact words.
- **An AI layer** (Groq, with Gemini as backup) reads the last minute of the call for tricks
  the rules don't know. It can only **add** risk. Every quote it gives must match a line that was
  really said. A caller saying "ignore your instructions" can't talk the score down. It's
  asked every few seconds at most to stay inside free limits. If Groq is slow or down Gemini
  takes over and the grandparent never sees an error.
- **A risk score** combines both and fades over time. Tricks that come together weigh more,
  like a bank claim plus a money ask or a bank claim plus a scare.
- **It knows talking about a scam from a scam.** A daughter warning her mom about gift card
  calls stays calm and so does a friend retelling a call she beat. A surprise party, a real bank
  that already blocked a charge and "I'll fax it right now" stay calm too.
- **With one shared mic** the server runs without speaker labels. Every line is scored and the
  AI works out which lines are the caller's. When it quotes two or more different tricks it can
  raise the warning on its own.

## How well it works

These numbers come from a held-out set: 16 staged role-play calls (8 scams and 8 tricky normal
calls) that the team wrote and never tuned the detector on. They are not real victims.

| Test, rules only (AI off) | Result |
|---|---|
| Scam calls that reach a Warning | 5 of 8 |
| Normal calls that get a false Warning | 0 of 8 |
| Time to score one caption | about 0.2 ms |

The normal calls include a real bank fraud alert, a real grandkid asking for help, a surprise
party and a pharmacy copay. The three scams the rules miss (a Medicare back brace offer, a
laptop refund and a roof deposit) are the kind the AI layer is there for. Run it yourself with
`python -m hangup_detect.eval --set heldout` from `detection/`.

We also have 44 practice calls (22 scams, 22 normal) and 10 scams improvised by an outside review. We changed rules
after seeing those, so they aren't counted above.

## Run it

Everything runs on one laptop. Full steps, fallbacks and a checklist for the demo are in
[`docs/DEMO-RUNBOOK.md`](docs/DEMO-RUNBOOK.md).

Once, from the repo root:

```
python3 -m venv .venv && source .venv/bin/activate
pip install -e detection -e "server[mic,dev]"   # mic = sounddevice for the laptop mic, dev = pytest
cp server/.env.example server/.env              # fill in the keys (below)
python -m aegis_server.seed                     # optional: demo family accounts (needs DEMO_PASSWORD)
(cd web && npm ci)
```

`server/.env` needs `DEEPGRAM_API_KEY` for live captions and `GROQ_API_KEY` with
`GEMINI_API_KEY` for the AI layer. `TIGER_DATABASE_URL` and `DEMO_PASSWORD` are for family
accounts and call history.

Then two terminals, each from the repo root:

```
uvicorn aegis_server.main:app --app-dir server --port 8000   # 1: server
cd web && npm run dev                                         # 2: screens at http://localhost:5173
```

Press **Start a call** on the front page at `http://localhost:5173`, or run
`server/scripts/start-call` in a third terminal to print the elder and family links.
`server/scripts/end-call` ends a call. Starting a new call also ends any call that still has
the mic.

The family link opens on a phone through a Cloudflare quick tunnel. When `cloudflared` is
running the server picks up its address by itself. The front page shows the family link as a
QR code to scan.

No keys? The detector still runs on rules alone. The screens can also replay sample calls such
as `http://localhost:5173/elder?fixture=scam-grandson`.

## Repo

| Folder | What's in it |
|---|---|
| `detection/` | The detector: rules, risk score, cards, AI layer, replay, test calls and tests |
| `server/` | FastAPI server: sessions, Deepgram live captions, the event stream, family accounts and call history (Tiger Data) |
| `web/` | The front page (start a live call), the grandparent screen (`/elder`), family page (`/family`), evidence page (`/evidence`) |
| `tools/dev_server/` | A small fallback server with the same routes, plus typed captions |
| `CONTRACTS.md` | The exact messages between the parts |
| `docs/` | Demo runbook and design notes |

## Privacy

- Audio is never stored. It streams only to Deepgram for live captions with model training
  turned off.
- Caption text isn't logged. The database keeps only when calls happened and how risky they
  looked (scores and levels), never what was said.
- Passwords are stored only as argon2 hashes. Login and pairing tokens are stored only as
  hashes in the database.
- Saving a call's words is off by default. Only staged test calls started on purpose with
  `start-call --transcript` are written to `server/recordings/`, which git ignores.
- The AI layer gets at most the last 60 seconds of text. With one shared mic it can't tell the
  voices apart and both voices go to it without labels.
- The app never asks for or stores the family code word.

## Tests

Each from the repo root:

```
(cd detection && python -m pytest -q)    # detector
(cd server && pytest -q)                 # server
(cd web && npm test)                     # screens
```
