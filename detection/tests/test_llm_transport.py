"""Live run found Groq's firewall (Cloudflare 1010) rejects Python's default User-Agent."""
import io
import json

from hangup_detect import llm_runner
from hangup_detect.llm_runner import DEFAULT_MODELS, http_transport

MSGS = [{"role": "system", "content": "s"}, {"role": "user", "content": "u"}]


def capture(monkeypatch, reply):
    seen = []

    def fake_urlopen(req, timeout):
        seen.append(req)
        return io.BytesIO(json.dumps(reply).encode())

    monkeypatch.setattr(llm_runner.urllib.request, "urlopen", fake_urlopen)
    return seen


def test_groq_call_sends_own_user_agent(monkeypatch):
    seen = capture(monkeypatch, {"choices": [{"message": {"content": "{}"}}]})
    http_transport({"GROQ_API_KEY": "k"})("groq", MSGS, 1.0)
    ua = seen[0].get_header("User-agent")
    assert ua and not ua.startswith("Python-urllib")


def test_gemini_call_sends_own_user_agent(monkeypatch):
    seen = capture(monkeypatch, {"candidates": [{"content": {"parts": [{"text": "{}"}]}}]})
    http_transport({"GEMINI_API_KEY": "k"})("gemini", MSGS, 1.0)
    ua = seen[0].get_header("User-agent")
    assert ua and not ua.startswith("Python-urllib")


def test_groq_default_model_is_not_the_retired_one():
    assert DEFAULT_MODELS["groq"] != "llama-3.1-8b-instant"  # 404 model_not_found on 2026-11-14


def test_gemini_default_model_is_not_the_retired_one():
    assert DEFAULT_MODELS["gemini"] != "gemini-2.5-flash"  # 404 "no longer available to new users" 2026-11-14
