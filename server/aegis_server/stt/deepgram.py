"""Laptop mic -> Deepgram streaming -> caption events (step 2; issue #3).

- Interim results and speaker labels (diarization) on; Deepgram's model-improvement opt-out on.
- A makes utterance_id (new one after each final) and revision (counts interim updates).
- Deepgram labels speakers per word, so one result is split into one caption per speaker.
- Sends a server `status` with stt="deepgram" when captions start (C7).
- Audio is streamed only, never written to disk.
"""
from __future__ import annotations


async def stream_mic(session_id: str) -> None:
    raise NotImplementedError
