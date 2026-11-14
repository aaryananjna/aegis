# Aegis

Aegis listens to a phone call on speaker and warns an older adult, in plain words on their
laptop screen, while a scammer is still talking. It catches what the caller **says** (bank
"fraud teams", gift cards, warrants, "don't tell anyone"), not what they sound like, so a
cloned voice doesn't get past it. A family member's phone gets an alert with the caller's own
words and a button to call back.

Built at HackUMass XIV (Nov 13 to 15, 2026) by Aryan Dubey (server and audio), Mihir
Kolakaluri (detection) and Aaryan Anjna (screens and demo).

## What it does on a call

1. The laptop mic hears the call on speakerphone. Deepgram turns it into live captions.
2. The detector scores every line for 8 scam tactics: pretending to be someone, rushing,
   secrecy, unusual payment, threats, dodging questions, remote control of a device and
   sounding panicked.
3. The grandparent's screen shows huge captions, highlights the risky words and moves from
   "Normal call" to "Be careful" to "Warning".
4. When it's likely a scam, one calm card appears:
   - the caller claims to be family: **"Ask: what's our family code word?"**
   - a bank, the government or a company: **"Don't pay or share any numbers. Say you'll call
     back."**
   - it keeps going: **"Hang up."** with who to call instead
5. The family page gets the same alert with the quotes, and "code word passed" if the caller
   got it right.
6. Family members can log in to see their grandparent's past calls: when they happened and how
   risky they looked. The grandparent never logs in; their laptop is paired once.

## How detection works

- **Rules** catch known scam wording instantly and point at the exact words.
- **An AI layer** (Groq, Gemini as backup) reads the caller's recent lines for tricks the
  rules don't know. It can only **add** risk: every quote it gives must match a real line, it's
  capped, and a caller saying "ignore your instructions" can't talk the score down. It's asked
  at most every 8 seconds, so a long call stays within free-tier limits.
- **A risk score** combines both, with decay over time and extra weight when tricks appear
  together (pretending to be the bank plus asking to move money).
- **With one shared mic** the server runs without speaker labels, so every line is scored, and
  the AI reads both voices and works out which lines are the caller's. When it quotes two or
  more different tricks, it can raise the warning on its own.

## Run it

Everything runs on one laptop. Full steps, fallbacks and a pre-demo checklist are in
[`docs/DEMO-RUNBOOK.md`](docs/DEMO-RUNBOOK.md).

Once, from the repo root:

```
python3 -m venv .venv && source .venv/bin/activate
pip install -e detection -e server
cp server/.env.example server/.env        # fill in the keys (below)
python -m aegis_server.seed               # optional: demo family accounts (needs DEMO_PASSWORD)
(cd web && npm ci)
```

`server/.env` needs `DEEPGRAM_API_KEY` for live captions, `GROQ_API_KEY` and `GEMINI_API_KEY`
for the AI layer (Gemini is the backup), and `TIGER_DATABASE_URL` and `DEMO_PASSWORD` for
family accounts and call history.

Then three terminals, each from the repo root:

```
uvicorn aegis_server.main:app --app-dir server --port 8000   # 1: server
cd web && npm run dev                                         # 2: screens at http://localhost:5173
server/scripts/start-call                                     # 3: starts a call, prints the elder and family links
```

`server/scripts/end-call` ends it.

No keys? The detector still runs on rules only, and the web app can replay sample calls:
`http://localhost:5173/elder?fixture=scam-grandson`.

## Repo

| Folder | What's in it |
|---|---|
| `detection/` | The detector: rules, risk score, cards, AI layer, replay, test calls and tests |
| `server/` | FastAPI server: sessions, Deepgram live captions, the event stream, family accounts and call history (TigerDB) |
| `web/` | The grandparent screen (`/elder`), family page (`/family`), evidence page (`/evidence`) |
| `tools/dev_server/` | A small fallback server with the same routes, plus typed captions |
| `CONTRACTS.md` | The exact messages between the parts |
| `docs/` | Demo runbook and design notes |

## Privacy

- Audio is never stored. It streams only to Deepgram for live captions, with model training
  turned off.
- Caption text isn't logged. The database keeps only when calls happened and how risky they
  looked (scores and levels), never what was said.
- Passwords are stored only as argon2 hashes. Login and pairing tokens are stored only as
  hashes.
- The AI layer gets at most the last 60 seconds of text. With one shared mic it can't tell
  the voices apart, so both voices go to it, unlabeled.
- The app never asks for or stores the family code word.

## Tests

Each from the repo root:

```
(cd detection && python -m pytest -q)    # detector
(cd server && pytest -q)                 # server
(cd web && npm test)                     # screens
```
