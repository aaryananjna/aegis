# Demo runbook

How to start everything for the demo, with exact commands, and what to do when something
breaks. The call script itself is in `detection/demo/README.md`.

**Status (14 Nov, 4 pm):** everything is on `main`: the screens, `tools/dev_server` and A's real
server (#38). Voice guessing and labels-off are in #39. Steps marked ⚠ haven't been tried end to
end yet.

Everything runs on the presenter's laptop. The family phone reaches it through a Cloudflare
quick tunnel over a phone hotspot (campus Wi-Fi often blocks device-to-device traffic).

```
laptop mic ─▶ server :8000 ─▶ /events ─▶ web (Vite) :5173 ─▶ /elder, /evidence on the laptop
                                                       └──▶ cloudflared ─▶ /family on the phone
```

## 0. Once, before the event

```
brew install node cloudflared          # Node 26 LTS, cloudflared 2026.11.0 (both tested)
python3 -m venv .venv && source .venv/bin/activate
pip install -e detection fastapi "uvicorn[standard]"
pip install -e "server[mic]"           # only if using A's server/; [mic] = sounddevice for the laptop mic
cd web && npm ci && npm test && cd ..
```

AI layer (optional): put `GROQ_API_KEY=…` (and `GEMINI_API_KEY=…` as backup) in the server's
environment. With no key it runs rules only, and `/evidence` says so.

## 1. Start (three terminals)

**Terminal 1, server.** Use A's server; the fallback has the same routes:

```
# A's server (preferred, has the laptop mic and Deepgram):
uvicorn aegis_server.main:app --app-dir server --port 8000

# Fallback (no mic: captions come from the typed fallback or a script):
uvicorn aegis_dev_server:app --app-dir tools/dev_server --port 8000
```

Check: `curl -s localhost:8000/health` should print `{"ok":true,...}`.

**Terminal 2, web:**

```
cd web && npm run dev                  # http://localhost:5173, forwards /events to :8000
```

**Terminal 3, tunnel for the family phone** ⚠ (`cloudflared` is installed and its flags are
checked; no tunnel was opened overnight):

```
cloudflared tunnel --url http://localhost:5173
```

It prints `https://<random-words>.trycloudflare.com`. Copy it:

```
export TUNNEL=https://<random-words>.trycloudflare.com
```

The tunnel points at the web app, not at :8000. The phone loads the page and its `/events`
socket through Vite's proxy, and the family token protects it. `/sessions`, `/typed` and
`/captions` aren't reachable from the phone at all: they're laptop only.

## 2. Start a call

For the demo, A's server runs the laptop mic **with speaker labels off** (#39/#40): one mic
hears both voices, and Deepgram's labels drift between them. Every line is scored from the start,
so nobody needs to tap. Keep Grandma's lines free of scam words ("Hello?", "Who is this?",
"Oh no", "Okay").

```
curl -s -X POST localhost:8000/sessions -H 'content-type: application/json' \
     -d '{"name":"Rose","phone":"+15550100","mic":true,"labels":false}' \
| python3 -c "import json,sys,os; d=json.load(sys.stdin); t=os.environ['TUNNEL']; print('session:', d['session_id']); print('elder:  ', d['elder_url']); print('family: ', d['family_url'].replace('http://localhost:5173', t))"
```

(Tested against `tools/dev_server` and A's server. Drop `"mic":true,"labels":false` for a
typed-only call.)

- Open **elder** on the laptop, full screen (Ctrl+Cmd+F in Chrome).
- Send **family** to the phone (AirDrop or a message to yourself) and open it **before** the
  call. It should say "Watching over Rose · Connected".
- Optional: open `http://localhost:5173/evidence?session=<id>&token=<elder token>` on a second
  laptop window for judges.
- **Labels off (the demo):** the elder screen shows "Aegis is listening." and "listening to
  everyone" at once. Nothing to tap.
- **Labels on:** the server guesses Grandma from her first "Hello?" and the screen says "We think
  this voice is you ✓". If it's wrong, tap the right voice under "Not you? Tap your voice". With
  no guess, tap the voice on "Tap the voice that is you".

End the call: `curl -s -X POST localhost:8000/sessions/<session>/end`. Both screens show
"Call ended".

## 3. When something breaks

| Problem | Do this |
|---|---|
| Hall too loud, captions wrong | **Typed fallback** (works with A's server and the fallback, both have `POST /typed`): `python tools/dev_server/typed_cli.py <session>`, then type `c: …` for the caller and `e: …` for the grandparent. Lines show a "typed" badge on the screen. Say so if asked. |
| A's server not ready or crashes | Switch terminal 1 to the fallback server, start a new call (section 2), and use the typed fallback. |
| Tunnel fails or the phone can't connect | Try a new tunnel. If that fails, open the family link on a second laptop: `http://localhost:5173/family?session=…&token=…`. |
| Everything live fails | **Sample calls**, labelled "Sample call" on screen. Say plainly it's a recorded sample, never live: `http://localhost:5173/elder?fixture=demo-bank`, `…/elder?fixture=scam-grandson`, `…/family?fixture=scam-grandson`, `…/evidence?fixture=demo-bank`. Add `&speed=2` to go faster. |
| Phone page asleep or "Reconnecting…" | Wake the phone. The page reconnects and the server replays the alerts it missed (C6). |
| "The server refused this link" | The token is wrong or the call ended. Start a new call. |

## 4. Pre-demo checklist

**30 minutes before**
- [ ] Laptop and phone charged; laptop on power.
- [ ] Phone hotspot on, laptop joined to it.
- [ ] `cd web && npm test` passes. `curl -s localhost:8000/health` shows `ok`.
- [ ] One full rehearsal of the scam call and the real-grandson call (`detection/demo/README.md`).
- [ ] Sample-call URLs open in hidden tabs, ready as the last fallback.

**5 minutes before**
- [ ] New call started (section 2). Elder screen full screen, browser zoom 100%.
- [ ] Family page open on the phone and showing "Connected". iPhone: Auto-Lock set to Never
  (the page also asks to keep the screen on). iPhone can't vibrate from a web page, so the card
  is the alert.
- [ ] Laptop: Do Not Disturb on, other tabs and notifications closed, no `.env` or keys on screen.
- [ ] The judge's phone on speaker about 10 cm from the laptop mic.

**During**
- [ ] Nothing to tap: speaker labels are off and every line is scored from the first one.
- [ ] After the code word card, the grandparent taps "They knew it" or "They didn't".
- [ ] Open `/evidence` for this call before it ends (the call's links stop working when it
  ends), then show the exact words behind each step.

**Honesty rules (CLAUDE.md):** made-up names and numbers only, never present a sample as live,
and judge-facing numbers come only from `detection/eval/calls/heldout/`, described as staged
role-play with counts.
