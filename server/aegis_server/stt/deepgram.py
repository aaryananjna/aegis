"""Laptop mic -> Deepgram streaming -> `caption` events.

Where the voice goes, and nowhere else: laptop mic -> this process (memory only) -> Deepgram,
over TLS with the certificate checked. No endpoint of ours accepts or returns audio, audio is
never written to disk or logged, and Deepgram's model-improvement opt-out (mip_opt_out) is on.
Only text captions come back.

Two ways to run it:
- Inside the server: POST /sessions {"mic": true} starts the mic for that call and stops it when
  the call ends. Captions go straight onto the session queue.
- As a separate process (for tools/dev_server, or to replay a WAV):
    python -m aegis_server.stt.deepgram <session_id>                  # laptop mic
    python -m aegis_server.stt.deepgram <session_id> --file call.wav  # 16-bit WAV, real time
    python -m aegis_server.stt.deepgram --list-devices
  It sends captions to ws://localhost:8000/captions/<session_id>. Ctrl+C stops it; --end also
  ends the call.

Caption text isn't printed unless --show. If Deepgram drops, it reconnects and keeps times
continuous.
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
from typing import AsyncIterator, Awaitable, Callable
from urllib.parse import urlencode, urlparse

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

Sink = Callable[[dict], Awaitable[None]]


class SttError(Exception):
    """Deepgram can't be used (bad key, certificate, no mic). Retrying won't help."""


def deepgram_params(model: str = "nova-3", diarize: bool = True) -> dict[str, str]:
    return {
        "model": model, "language": "en", "encoding": "linear16", "sample_rate": str(RATE),
        "channels": "1", "interim_results": "true", "diarize": str(diarize).lower(),
        "punctuate": "true", "smart_format": "true", "endpointing": "300",
        "mip_opt_out": "true",
    }


def _check_url(url: str) -> None:
    """Voice only ever goes to Deepgram over TLS (plain ws:// only to a local fake, for tests)."""
    u = urlparse(url)
    if u.scheme == "wss" and u.hostname == "api.deepgram.com":
        return
    if u.scheme == "ws" and u.hostname in ("127.0.0.1", "localhost", "::1"):
        return
    raise SttError(f"refusing to send audio to {u.scheme}://{u.hostname}")


# ---- audio sources: each yields 100 ms chunks of 16 kHz mono 16-bit PCM ------------------

async def mic_chunks(device: int | str | None, stop: asyncio.Event) -> AsyncIterator[bytes]:
    try:
        import sounddevice as sd  # optional: pip install -e "server[mic]"
    except ImportError as e:
        raise SttError('the mic needs sounddevice: pip install -e "server[mic]"') from e

    loop = asyncio.get_running_loop()
    q: asyncio.Queue[bytes] = asyncio.Queue(maxsize=100)  # ~10 s; oldest dropped if stuck

    def on_audio(indata, frames, t, status):  # PortAudio thread
        data = bytes(indata)

        def put():
            if q.full():
                q.get_nowait()
            q.put_nowait(data)
        loop.call_soon_threadsafe(put)

    try:
        stream = sd.RawInputStream(samplerate=RATE, channels=1, dtype="int16", device=device,
                                   blocksize=int(RATE * CHUNK_S), callback=on_audio)
    except Exception as e:  # PortAudioError, bad device
        raise SttError(f"can't open the mic: {e}") from e
    with stream:
        while not stop.is_set():
            try:
                yield await asyncio.wait_for(q.get(), timeout=0.5)
            except asyncio.TimeoutError:
                continue


async def wav_chunks(path: Path, stop: asyncio.Event) -> AsyncIterator[bytes]:
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
    for _ in range(15):  # a little silence so Deepgram finalizes the last words
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


async def transcribe(session_id: str, source: AsyncIterator[bytes], sink: Sink, *,
                     api_key: str, model: str = "nova-3", diarize: bool = True,
                     stop: asyncio.Event | None = None, deepgram_url: str = DEEPGRAM_URL,
                     on_connect: Callable[[], Awaitable[None]] | None = None) -> Stats:
    """Stream `source` to Deepgram and hand each caption to `sink`, until the audio ends,
    `stop` is set or the task is cancelled. Reconnects when Deepgram drops."""
    if not api_key:
        raise SttError("DEEPGRAM_API_KEY is not set in server/.env")
    _check_url(deepgram_url)
    stop = stop or asyncio.Event()
    stats = Stats()
    maker = CaptionMaker(session_id)
    url = f"{deepgram_url}?{urlencode(deepgram_params(model, diarize))}"
    audio_done = asyncio.Event()
    pending: asyncio.Queue[bytes | None] = asyncio.Queue(maxsize=100)
    t_start = time.monotonic()
    pump_error: list[BaseException] = []

    async def pump_audio():
        try:
            async for chunk in source:
                if pending.full():
                    pending.get_nowait()  # Deepgram is behind or reconnecting; drop the oldest
                pending.put_nowait(chunk)
        except Exception as e:  # mic failed: stop the whole pipe with its error
            pump_error.append(e)
        finally:
            audio_done.set()
            if pending.full():
                pending.get_nowait()
            pending.put_nowait(None)

    async def emit(cap: dict) -> None:
        stats.captions += 1
        if cap["speaker_raw"] is not None:
            stats.speakers.add(cap["speaker_raw"])
        if cap["text"]:
            behind = (time.monotonic() - t_start) - cap["end_s"]
            stats.lag.append(behind)
            if cap["is_final"]:
                stats.finals += 1
                stats.final_lag.append(behind)
        await sink(cap)

    pump = asyncio.create_task(pump_audio())
    failures = 0
    try:
        while not pump_error:
            maker.offset_s = stats.sent_s
            try:
                async with websockets.connect(
                        url, additional_headers={"Authorization": f"Token {api_key}"},
                        open_timeout=10, max_size=2**22,
                        ssl=SSL if url.startswith("wss:") else None) as dg:
                    log.info("Deepgram connected (%s, diarize=%s)", model, diarize)
                    failures = 0
                    if on_connect:
                        await on_connect()

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
                            if isinstance(raw, bytes):
                                continue
                            msg = json.loads(raw)
                            if msg.get("type") == "Error" or "err_code" in msg:
                                log.error("Deepgram error: %s",
                                          msg.get("description") or msg.get("err_code"))
                            for cap in maker.feed(msg):
                                await emit(cap)
                    finally:
                        snd.cancel()
                if audio_done.is_set() or stop.is_set():
                    break  # normal close after CloseStream
            except ssl.SSLCertVerificationError as e:
                raise SttError(f"can't verify Deepgram's certificate: {e}") from e
            except websockets.InvalidStatus as e:
                if e.response.status_code in (401, 403):
                    raise SttError("Deepgram rejected the key (check DEEPGRAM_API_KEY)") from e
                failures += 1
                log.warning("Deepgram refused (HTTP %s); retrying", e.response.status_code)
            except (OSError, websockets.WebSocketException, asyncio.TimeoutError) as e:
                if audio_done.is_set() or stop.is_set():
                    break
                failures += 1
                log.warning("Deepgram dropped (%s); reconnecting", type(e).__name__)
            for cap in maker.close_open():
                await emit(cap)
            await asyncio.sleep(min(5.0, 0.5 * 2 ** min(failures, 4)))  # back off, max 5 s
        for cap in maker.close_open():
            await emit(cap)
    finally:
        pump.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await pump
    if pump_error:
        raise pump_error[0]
    return stats


# ---- separate-process mode ---------------------------------------------------------------

async def run(session_id: str, *, server: str, source_iter, api_key: str, model: str,
              diarize: bool, show: bool, end_call: bool,
              stop: asyncio.Event | None = None) -> Stats:
    """Captions to a server's /captions socket (A's server or tools/dev_server)."""
    async with websockets.connect(f"{server}/captions/{session_id}", open_timeout=5) as srv:
        log.info("connected to %s", server)

        async def sink(cap: dict) -> None:
            await srv.send(json.dumps(cap))
            if show and cap["is_final"] and cap["text"]:
                print(f"  [{cap['speaker_raw']}] {cap['text']}")

        stats = await transcribe(session_id, source_iter, sink, api_key=api_key, model=model,
                                 diarize=diarize, stop=stop)
        if end_call:
            await srv.send(json.dumps({"type": "end", "session_id": session_id}))
    return stats


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
    if urlparse(a.server).hostname not in ("127.0.0.1", "localhost", "::1"):
        p.error("--server must be on this laptop (captions carry what's said on the call)")

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
    except SttError as e:
        raise SystemExit(str(e))
    _report(stats)


if __name__ == "__main__":
    main()
