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
d.end(now_s)                                       # call over; the detector refuses input after
```

Every call returns a list of event dicts (`tactic_set`, `risk`, `intervention`, `alert`,
`status`). Forward them to C's screens as they are. `now_s` is seconds since the call started.

## Three rules

1. **One owner per session.** The Detector is not thread safe. Put captions, ticks, the elder
   tap and the end of the call on one `asyncio.Queue` and let one task handle them in order.
2. **Tick every second.** Without ticks the meter can't calm down when the call goes quiet.
3. **Cards and alerts wait for `set_elder`.** Until C's screen sends who the grandparent is,
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
and `fixtures/events-benign-party.jsonl`.

## Data

With the rules only (today) nothing leaves the server. When the AI layer is added later,
only the caller's last 60 seconds of text goes to Groq or Gemini.
