"""LLM provider abstraction.

The enrichment layer needs exactly one operation from a provider: given a prompt,
return a validated LlmResult plus a token count. Providers are swappable via env:
set GROQ_API_KEY or GEMINI_API_KEY and the right one is chosen automatically.
Adding another (Claude, OpenAI, ...) is one more `_call_*` function and a branch.
"""

from __future__ import annotations

import logging
import os
import time

import httpx
from pydantic import BaseModel

log = logging.getLogger("jobradar")

MAX_RETRIES = 3

GEMINI_MODEL = "gemini-2.5-flash"
GROQ_MODEL = "llama-3.3-70b-versatile"

GEMINI_ENDPOINT = (
    f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"
)
GROQ_ENDPOINT = "https://api.groq.com/openai/v1/chat/completions"

# Gemini enforces this natively; for Groq the shape is described in the prompt.
GEMINI_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "summary": {"type": "STRING"},
        "salary_min": {"type": "INTEGER", "nullable": True},
        "salary_max": {"type": "INTEGER", "nullable": True},
        "salary_currency": {"type": "STRING", "nullable": True},
    },
    "required": ["summary"],
}


class LlmResult(BaseModel):
    summary: str
    salary_min: int | None = None
    salary_max: int | None = None
    salary_currency: str | None = None


class KeyDenied(Exception):
    """Key missing/invalid or project denied; skip the LLM step entirely."""


def _sleep_backoff(attempt: int) -> None:
    time.sleep(2**attempt * 5)


def _call_gemini(client: httpx.Client, key: str, prompt: str) -> tuple[LlmResult, int]:
    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "responseMimeType": "application/json",
            "responseSchema": GEMINI_SCHEMA,
            "temperature": 0.1,
        },
    }
    for attempt in range(MAX_RETRIES):
        resp = client.post(GEMINI_ENDPOINT, params={"key": key}, json=body, timeout=45)
        if resp.status_code == 200:
            payload = resp.json()
            text = payload["candidates"][0]["content"]["parts"][0]["text"]
            tokens = payload.get("usageMetadata", {}).get("totalTokenCount", 0)
            return LlmResult.model_validate_json(text), tokens
        if resp.status_code in (401, 403):
            raise KeyDenied(f"{resp.status_code}: {resp.text[:120]}")
        if resp.status_code == 429:
            log.warning("gemini rate limited, backing off")
            _sleep_backoff(attempt)
            continue
        resp.raise_for_status()
    raise httpx.HTTPError("gemini: exhausted retries")


def _call_groq(client: httpx.Client, key: str, prompt: str) -> tuple[LlmResult, int]:
    body = {
        "model": GROQ_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "response_format": {"type": "json_object"},
        "temperature": 0.1,
    }
    headers = {"Authorization": f"Bearer {key}"}
    for attempt in range(MAX_RETRIES):
        resp = client.post(GROQ_ENDPOINT, headers=headers, json=body, timeout=45)
        if resp.status_code == 200:
            payload = resp.json()
            text = payload["choices"][0]["message"]["content"]
            tokens = payload.get("usage", {}).get("total_tokens", 0)
            return LlmResult.model_validate_json(text), tokens
        if resp.status_code in (401, 403):
            raise KeyDenied(f"{resp.status_code}: {resp.text[:120]}")
        if resp.status_code == 429:
            log.warning("groq rate limited, backing off")
            _sleep_backoff(attempt)
            continue
        resp.raise_for_status()
    raise httpx.HTTPError("groq: exhausted retries")


def select_provider():
    """Return (name, model, key, call_fn) for the configured provider, or None.

    Groq wins if both keys are set: it has a no-billing free tier that works
    everywhere, so it is the safer default for this project.
    """
    if key := os.environ.get("GROQ_API_KEY"):
        return ("groq", GROQ_MODEL, key, _call_groq)
    if key := os.environ.get("GEMINI_API_KEY"):
        return ("gemini", GEMINI_MODEL, key, _call_gemini)
    return None
