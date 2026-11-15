"""One real AI layer call. Skips cleanly with no key.

    cd detection && python scripts/llm_smoke.py

Reads GROQ_API_KEY / GEMINI_API_KEY from the environment or detection/.env. Prints the
provider, the model, how long it took and what the guard kept. Never prints the key.
"""
import asyncio
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from hangup_detect.guard import parse_llm  # noqa: E402
from hangup_detect.llm_runner import DEFAULT_MODELS, LLMRunner  # noqa: E402
from hangup_detect.types import LLMRequest  # noqa: E402


def load_env():
    env = dict(os.environ)
    f = Path(__file__).resolve().parents[1] / ".env"
    if f.exists():
        for line in f.read_text().splitlines():
            k, sep, v = line.partition("=")
            if sep and k.strip() and not k.startswith("#"):
                env.setdefault(k.strip(), v.strip().strip('"').strip("'"))
    return env


async def main():
    env = load_env()
    runner = LLMRunner.from_env(env)
    if runner is None:
        print("SKIP: no GROQ_API_KEY or GEMINI_API_KEY (rules only)")
        return 0
    runner.total_s = runner.socket_s = 5.0  # first call can be slow; the demo uses 3 s total, 1.4 s per provider
    utts = (("u1", "Hi, this is the security team at your bank."),
            ("u2", "Go to the store, get Target cards and call me back with the codes."))
    t0 = time.monotonic()
    result = await runner.run(LLMRequest(1, utts, 0.0))
    ms = (time.monotonic() - t0) * 1000
    model = env.get(f"{(result.provider or 'groq').upper()}_MODEL") or DEFAULT_MODELS.get(result.provider or "groq")
    print(f"provider={result.provider} model={model} mode={result.mode} took={ms:.0f} ms error={result.error}")
    kept = parse_llm(result.raw or "", dict(utts), 0.0)
    print(f"guard kept {len(kept)}:", [(e.tactic.value, e.quote) for e in kept])
    return 0 if result.raw else 1


sys.exit(asyncio.run(main()))
