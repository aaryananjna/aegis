# Using the detector from A's server

Based on the **draft** event list in CONTRACTS (not yet agreed by the whole team).

## Install

```
pip install -e detection        # no runtime dependencies, Python 3.11+
```

## The whole API

```python
from hangup_detect import Config, Detector, make_segment

d = Detector(Config(), session_id)                 # one per call
d.feed(make_segment(utterance_id, revision, "unknown", text,
                    start_s, end_s, is_final, speaker_raw="0"), now_s)   # every caption
d.tick(now_s)                                      # every 1.0 s, even in silence
d.set_elder("0", now_s)                            # C's "who is the grandparent?" tap (None = no labels)
d.codeword_result(True, now_s)                     # C's "did they give the right code word?" answer
d.end(now_s)                                       # call over; the detector refuses input after
```

Every call returns a list of event dicts (`tactic_set`, `risk`, `intervention`, `alert`,
`status`). Forward them to C's screens as they are. `now_s` is seconds since the call started.

## Three rules

1. **One owner per session.** The Detector is not thread safe. Put captions, ticks, the elder
   tap and the end of the call on one `asyncio.Queue` and let one task handle them in order.
2. **Tick every second.** Without ticks the meter can't calm down when the call goes quiet.
3. **The code word answer (C12).** When the `codeword` card is up, the elder screen sends
   `{"type": "codeword_result", "ok": true|false}`. Pass `ok` to `codeword_result`. Wrong
   answer: the hang up card and its alert come back at once. Right answer: one
   `{"type": "codeword_ok", "resolves": "<session>:codeword", ...}` event (send it to the
   family page too, so they see it was handled), then no score-based hang up, but a dodge
   still escalates. Any other time it returns a `status` warning.
4. **Cards and alerts wait for `set_elder`.** Until C's screen sends who the grandparent is,
   the meter moves but no card or family alert fires, so Grandma's own words can't set one
   off. Speaker labels come from Deepgram diarization (`speaker_raw`).

A complete runnable example is in `examples/server_example.py`.

## What A owns

- Deepgram, the WebSocket server and session lifecycle.
- **Family-page access:** a random token per session that opens only that session, read
  only, expires at session end and is checked on every connect and reconnect.
- Logging: don't log caption text by default. API keys stay on the server.

## Try it without audio

```
python -m hangup_detect.replay examples/scam-grandson.call --elder 0          # readable
python -m hangup_detect.replay examples/scam-grandson.call --elder 0 --json   # what C receives
python -m hangup_detect.cli                                                    # type a call
```

Ready-made event streams for building C's screens: `fixtures/events-scam-grandson.jsonl`
and `fixtures/events-benign-party.jsonl`. They include the `caption` events A will forward
(with `t`, no `seq`), in order, so the `/elder` screen can show live captions and line up the
highlight spans with the caption text. Regenerate with `--json --captions`.

## AI layer (optional, S8a)

Set `GROQ_API_KEY` (and optionally `GEMINI_API_KEY` as backup) in the server's environment.
With no key it stays rules only and nothing else changes. `examples/server_example.py` shows
the pattern:

1. After each queue item, if the runner isn't busy, call `d.llm_request(now)`.
2. If it returns a request, run it in a task (`await runner.run(req)`, 1.5 s budget) and put
   `("llm", (req.seq, result))` back on the same queue.
3. The owner calls `d.llm_status(result.mode, now, result.error)` and, if there's an answer,
   `d.apply_llm(seq, result.raw, now)`.

Rules the detector enforces for you:
- Labels on: it only sends anything after the grandparent tap names a speaker, and then
  only the caller's last 60 s of text.
- Labels off (`set_elder(None)`, one shared mic): nothing is sent until a rule flags a line.
  Then the last 60 s of both voices goes unlabeled, with a prompt that has the AI work out
  which lines are the caller's and flag only those (`Config(llm_mixed=False)` turns this off).
- AI evidence must quote real words from the lines sent, can only add risk (capped), can't make the level
  HIGH alone and can't trigger a card by itself. Late or repeated answers are dropped.

Live check once a key exists: `python scripts/llm_smoke.py` (reads `detection/.env`).

## Data

With rules only, no text leaves the server. With an AI key set, the caller's last 60 seconds
of text goes to Groq (or Gemini as backup), and only after the grandparent tap. With labels
off, both voices' last 60 seconds go, and only after a rule has flagged a line.
