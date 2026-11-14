"""Test transcripts: save a staged call's final lines as a `.call` file for B's eval.

Off unless a call is started with `"save_transcript": true` (`start-call --transcript`), and
only for staged role-play with made-up names. Files go to server/recordings/ (gitignored) on
this laptop, never to the database, and are written when the call ends.

The file is a draft for detection/eval/calls/heldout/ (see the README there): fill in label,
group and onset_s, check who is the grandparent, fix any misheard words, then copy it over.
"""
from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path

log = logging.getLogger("aegis.transcripts")

DIR = Path(__file__).resolve().parent.parent / "recordings"


class TestTranscript:
    def __init__(self, session_id: str) -> None:
        self.session_id = session_id
        self.lines: dict[str, tuple[float, float, str | None, str]] = {}  # by utterance_id

    def add(self, seg) -> None:
        if seg.is_final and seg.text.strip():
            self.lines[seg.utterance_id] = (seg.start_s, seg.end_s, seg.speaker_raw,
                                            seg.text.strip())

    def write(self, elder_raw: str | None) -> Path | None:
        if not self.lines:
            return None
        try:
            DIR.mkdir(exist_ok=True)
            stamp = datetime.now().strftime("%Y%m%d-%H%M")
            path = DIR / f"{stamp}-{self.session_id}.call"
            speakers = sorted({s for _, _, s, _ in self.lines.values() if s is not None})
            head = [
                f"# id: heldout-XX-{self.session_id}      # TODO: heldout-NN-short-name",
                "# label: TODO                     # scam or benign",
                "# source: team-staged",
                "# set: heldout",
                "# group: TODO                     # script idea; never reuse a dev group",
                "# onset_s: TODO                   # scam calls: first scam move (delete if benign)",
            ]
            if speakers:
                guess = elder_raw if elder_raw in speakers else speakers[0]
                head.append(f"# elder: {guess}                      # check: which spkN is the grandparent")
            else:
                head.append("# note: no speaker labels; change each line to caller: or elder:")
            head.append(f"# note: Deepgram transcript, staged role-play, made-up names. Voices seen: {speakers or 'none'}")
            body = []
            for start, end, spk, text in sorted(self.lines.values()):
                who = f"spk{spk}" if spk is not None else "unknown"
                body.append(f"[{start:.1f}-{end:.1f}] {who}: {text}")
            path.write_text("\n".join(head + body) + "\n")
            print(f"\n  Test transcript saved: {path}\n", flush=True)
            return path
        except Exception as e:
            log.warning("couldn't save the test transcript (%s)", type(e).__name__)
            return None
