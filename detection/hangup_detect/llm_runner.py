"""Calls the AI layer without ever slowing the call down.

- Groq first, Gemini as backup, then rules only.
- One request at a time per session. A timed-out request's thread can't be killed, so the
  runner stays `busy` until that thread returns, and the owner skips new requests meanwhile.
- 1.5 s total budget. Late answers are simply never applied.
- Keys are sent in headers only and never appear in errors or logs.
Model names come from GROQ_MODEL / GEMINI_MODEL. Both defaults checked live 2026-11-14: Groq ~340 ms, Gemini ~0.8 to 1.4 s.
"""
from __future__ import annotations

import asyncio
import json
import time
import urllib.request
from dataclasses import dataclass

from .llm import build_messages
from .types import LLMRequest

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
USER_AGENT = "aegis-detect/0.1"  # Groq's firewall blocks the default Python-urllib agent
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
DEFAULT_MODELS = {"groq": "qwen/qwen3.8-27b", "gemini": "gemini-3.5-flash-lite"}


@dataclass(frozen=True)
class LLMResult:
    raw: str | None
    provider: str | None
    mode: str           # "full" or "rules_only"
    error: str | None = None


class LLMRunner:
    def __init__(self, transport, providers: list[str], total_s: float = 1.5, socket_s: float = 1.2):
        self.transport = transport
        self.providers = providers
        self.total_s = total_s
        self.socket_s = socket_s
        self._pending: asyncio.Future | None = None

    @property
    def busy(self) -> bool:
        return self._pending is not None and not self._pending.done()

    async def run(self, req: LLMRequest) -> LLMResult:
        loop = asyncio.get_running_loop()
        messages = build_messages(req.utterances)
        start = time.monotonic()
        error = "no provider"
        for provider in self.providers:
            left = self.total_s - (time.monotonic() - start)
            if left <= 0:
                break
            fut = loop.run_in_executor(None, self.transport, provider, messages, min(self.socket_s, left))
            self._pending = fut
            try:
                raw = await asyncio.wait_for(asyncio.shield(fut), left)
                return LLMResult(raw, provider, "full")
            except asyncio.TimeoutError:
                error = f"{provider} timed out"
                break  # its thread is still running; stay busy until it returns
            except Exception as exc:  # network or HTTP error: try the next provider
                error = f"{provider} failed: {type(exc).__name__}"
        return LLMResult(None, None, "rules_only", error)

    @classmethod
    def from_env(cls, env) -> "LLMRunner | None":
        providers = [p for p, k in (("groq", "GROQ_API_KEY"), ("gemini", "GEMINI_API_KEY")) if env.get(k)]
        if not providers:
            return None
        return cls(http_transport(env), providers)


def http_transport(env):
    """Real HTTP calls with stdlib urllib. Returns the model's text reply."""
    def call(provider: str, messages: list[dict], timeout_s: float) -> str:
        model = env.get(f"{provider.upper()}_MODEL") or DEFAULT_MODELS[provider]
        if provider == "groq":
            body = {"model": model, "messages": messages, "temperature": 0,
                    "response_format": {"type": "json_object"}, "max_tokens": 400}
            req = urllib.request.Request(GROQ_URL, json.dumps(body).encode(), method="POST", headers={
                "Authorization": f"Bearer {env['GROQ_API_KEY']}", "Content-Type": "application/json",
                "User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=timeout_s) as r:
                return json.load(r)["choices"][0]["message"]["content"]
        body = {"systemInstruction": {"parts": [{"text": messages[0]["content"]}]},
                "contents": [{"role": "user", "parts": [{"text": messages[1]["content"]}]}],
                "generationConfig": {"responseMimeType": "application/json", "temperature": 0}}
        req = urllib.request.Request(GEMINI_URL.format(model=model), json.dumps(body).encode(),
                                     method="POST", headers={"x-goog-api-key": env["GEMINI_API_KEY"],
                                                             "Content-Type": "application/json",
                                                             "User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=timeout_s) as r:
            return json.load(r)["candidates"][0]["content"]["parts"][0]["text"]
    return call
