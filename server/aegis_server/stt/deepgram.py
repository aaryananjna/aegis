"""Laptop mic -> Deepgram streaming -> `caption` events on the server's /captions socket.

Run (from server/, with DEEPGRAM_API_KEY in server/.env):

    python -m aegis_server.stt.deepgram <session_id>                  # laptop mic
    python -m aegis_server.stt.deepgram <session_id> --file call.wav  # a 16-bit WAV, real time
    python -m aegis_server.stt.deepgram --list-devices

It connects to ws://localhost:8000/captions/<session_id> (A's server or C's tools/dev_server;
same route). Ctrl+C stops it; add --end to also end the call.

- Deepgram Nova-3, interim results and speaker labels (diarize) on, and Deepgram's
  model-improvement opt-out (mip_opt_out) on.
- Audio is streamed only, never written to disk. Caption text isn't printed unless --show.
- If Deepgram drops, it reconnects and keeps the caption times continuous.
"""
from __future__ import annotations

import argparse
import asyncio
import contextlib
import json
import logging
import ssl
import time
import wave
from pathlib import Path
from urllib.parse import urlencode

import certifi
import websockets

from ..config import settings
from .captions import CaptionMaker

log = logging.getLogger("aegis.deepgram")

RATE = 16000
CHUNK_S = 0.1                       # 100 ms of audio per message
CHUNK_BYTES = int(RATE * CHUNK_S) * 2
DEEPGRAM_URL = "wss://api.deepgram.com/v1/listen"
# certifi's roots: python.org builds on macOS ship without system certificates.
SSL = ssl.create_default_context(cafile=certifi.where())


def deepgram_params(model: str = "nova-3", diarize: bool = True) -> dict[str, str]:
    return {
        "model": model, "language": "en", "encoding": "linear16", "sample_rate": str(RATE),
        "channels": "1", "interim_results": "true", "diarize": str(diarize).lower(),
        "punctuate": "true", "smart_format": "true", "endpointing": "300",
        "mip_opt_out": "true",
    }


# ---- audio sources: each yields 100 ms chunks of 16 kHz mono 16-bit PCM ------------------

async def mic_chunks(device: int | str | None, stop: asyncio.Event):
    import sounddevice as sd  # imported here so the server itself doesn't need PortAudio

    loop = asyncio.get_running_loop()
    q: asyncio.Queue[bytes] = asyncio.Queue(maxsize=100)  # ~10 s; oldest dropped if stuck

    def on_audio(indata, frames, t, status):  # PortAudio thread
        data = bytes(indata)

        def put():
            if q.full():
                q.get_nowait()
            q.put_nowait(data)
        loop.call_soon_threadsafe(put)

    with sd.RawInputStream(samplerate=RATE, channels=1, dtype="int16", device=device,
                           blocksize=int(RATE * CHUNK_S), callback=on_audio):
        while not stop.is_set():
            try:
                yield await asyncio.wait_for(q.get(), timeout=0.5)
            except asyncio.TimeoutError:
                continue


async def wav_chunks(path: Path, stop: asyncio.Event):
    with wave.open(str(path), "rb") as w:
        if (w.getframerate(), w.getnchannels(), w.getsampwidth()) != (RATE, 1, 2):
            raise SystemExit(f"{path}: need 16 kHz mono 16-bit WAV. Convert with:\n"
                             f"  afconvert -f WAVE -d LEI16@16000 -c 1 in.wav out.wav")
        t0 = time.monotonic()
        n = 0
        while not stop.is_set():
            data = w.readframes(int(RATE * CHUNK_S))
            if not data:
                break
            yield data
            n += 1
            await asyncio.sleep(max(0.0, t0 + n * CHUNK_S - time.monotonic()))  # real time
    # A little silence so Deepgram finalizes the last words.
    for _ in range(15):
        yield b"\x00" * CHUNK_BYTES
        await asyncio.sleep(CHUNK_S)


# ---- the pipe ----------------------------------------------------------------------------

class Stats:
    def __init__(self) -> None:
        self.sent_s = 0.0
        self.captions = 0
        self.finals = 0
        self.speakers: set[str] = set()
        self.lag: list[float] = []        # how far each caption trails its last word
        self.final_lag: list[float] = []  # same, final lines only (includes end-of-sentence wait)


async def run(session_id: str, *, server: str, source_iter, api_key: str, model: str,
              diarize: bool, show: bool, end_call: bool, deepgram_url: str = DEEPGRAM_URL,
              stop: asyncio.Event | None = None) -> Stats:
    stop = stop or asyncio.Event()
    stats = Stats()
    maker = CaptionMaker(session_id)
    url = f"{deepgram_url}?{urlencode(deepgram_params(model, diarize))}"
    audio_done = asyncio.Event()
    pending: asyncio.Queue[bytes | None] = asyncio.Queue(maxsize=100)
    t_start = time.monotonic()

    async def pump_audio():
        async for chunk in source_iter:
            if pending.full():
                pending.get_nowait()  # Deepgram is behind or reconnecting; drop the oldest
            pending.put_nowait(chunk)
        audio_done.set()
        await pending.put(None)

    async with websockets.connect(f"{server}/captions/{session_id}",
                                  open_timeout=5) as srv:
        log.info("connected to %s", server)

        async def send_caption(cap: dict) -> None:
            await srv.send(json.dumps(cap))
            stats.captions += 1
            if cap["speaker_raw"] is not None:
                stats.speakers.add(cap["speaker_raw"])
            if cap["text"]:
                behind = (time.monotonic() - t_start) - cap["end_s"]
                stats.lag.append(behind)
                if cap["is_final"]:
                    stats.finals += 1
                    stats.final_lag.append(behind)
            if show and cap["is_final"] and cap["text"]:
                print(f"  [{cap['speaker_raw']}] {cap['text']}")

        pump = asyncio.create_task(pump_audio())
        try:
            while True:
                maker.offset_s = stats.sent_s
                try:
                    async with websockets.connect(
                            url, additional_headers={"Authorization": f"Token {api_key}"},
                            open_timeout=10, max_size=2**22,
                            ssl=SSL if url.startswith("wss:") else None) as dg:
                        log.info("Deepgram connected (%s, diarize=%s)", model, diarize)

                        async def sender():
                            while True:
                                chunk = await pending.get()
                                if chunk is None:
                                    await dg.send(json.dumps({"type": "CloseStream"}))
                                    return
                                await dg.send(chunk)
                                stats.sent_s += len(chunk) / 2 / RATE

                        snd = asyncio.create_task(sender())
                        try:
                            async for raw in dg:
                                msg = json.loads(raw)
                                if msg.get("type") == "Error" or "err_code" in msg:
                                    log.error("Deepgram error: %s", msg.get("description")
                                              or msg.get("err_msg") or msg)
                                for cap in maker.feed(msg):
                                    await send_caption(cap)
                        finally:
                            snd.cancel()
                    if audio_done.is_set() or stop.is_set():
                        break  # normal close after CloseStream
                except (OSError, websockets.WebSocketException) as e:
                    if isinstance(e, ssl.SSLCertVerificationError):
                        raise SystemExit(f"can't verify Deepgram's certificate: {e}")
                    if isinstance(e, websockets.InvalidStatus) and \
                            e.response.status_code in (401, 403):
                        raise SystemExit("Deepgram rejected the key (check DEEPGRAM_API_KEY)")
                    if audio_done.is_set() or stop.is_set():
                        break
                    log.warning("Deepgram dropped (%s); reconnecting", type(e).__name__)
                for cap in maker.close_open():
                    await send_caption(cap)
                await asyncio.sleep(1)
            for cap in maker.close_open():
                await send_caption(cap)
            if end_call:
                await srv.send(json.dumps({"type": "end", "session_id": session_id}))
        finally:
            pump.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await pump
    return stats


async def stream_mic(session_id: str, device: int | str | None = None,
                     server: str = "ws://localhost:8000") -> Stats:
    """Used by the server once it starts the mic itself; same as the CLI without --file."""
    stop = asyncio.Event()
    return await run(session_id, server=server, source_iter=mic_chunks(device, stop),
                     api_key=settings.deepgram_api_key, model="nova-3", diarize=True,
                     show=False, end_call=False, stop=stop)


def _pct(xs: list[float]) -> str:
    xs = sorted(xs)
    return f"median {xs[len(xs) // 2]:.2f} s, p90 {xs[int(len(xs) * 0.9)]:.2f} s" if xs else "n/a"


def _report(stats: Stats) -> None:
    print(f"audio sent: {stats.sent_s:.1f} s · captions: {stats.captions} "
          f"({stats.finals} final lines) · speakers: {sorted(stats.speakers) or 'none'}")
    print(f"captions behind speech: {_pct(stats.lag)} · final lines: {_pct(stats.final_lag)}")


def main() -> None:
    p = argparse.ArgumentParser(description="Mic (or WAV) -> Deepgram -> /captions")
    p.add_argument("session_id", nargs="?")
    p.add_argument("--server", default="ws://localhost:8000")
    p.add_argument("--file", type=Path, help="stream a 16 kHz mono 16-bit WAV instead of the mic")
    p.add_argument("--device", help="mic number or name (see --list-devices)")
    p.add_argument("--list-devices", action="store_true")
    p.add_argument("--model", default="nova-3")
    p.add_argument("--no-diarize", action="store_true", help="no speaker labels")
    p.add_argument("--show", action="store_true", help="print final caption text (off by default)")
    p.add_argument("--end", action="store_true", help="end the call when this stops")
    a = p.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", datefmt="%H:%M:%S")

    if a.list_devices:
        import sounddevice as sd
        print(sd.query_devices())
        return
    if not a.session_id:
        p.error("session_id is required (from POST /sessions)")
    if not settings.deepgram_api_key:
        raise SystemExit("DEEPGRAM_API_KEY is not set in server/.env")

    device = int(a.device) if a.device and a.device.isdigit() else a.device
    stop = asyncio.Event()
    src = wav_chunks(a.file, stop) if a.file else mic_chunks(device, stop)

    async def go():
        task = asyncio.create_task(run(
            a.session_id, server=a.server, source_iter=src, api_key=settings.deepgram_api_key,
            model=a.model, diarize=not a.no_diarize, show=a.show, end_call=a.end, stop=stop))
        try:
            return await asyncio.shield(task)
        except asyncio.CancelledError:  # Ctrl+C: let Deepgram finish the last words
            stop.set()
            return await task

    try:
        stats = asyncio.run(go())
    except KeyboardInterrupt:
        print("stopped")
        return
    _report(stats)


if __name__ == "__main__":
    main()
