"""LLM enrichment layer (Gemini 2.5 Flash via REST).

This runs *after* the deterministic layer and upgrades heuristic rows with the
two things rules cannot do well: a one-line human summary and a salary parsed
out of prose. Region / remote / seniority / stack stay as the rule-based values.

Designed around free-tier reality: bounded per run, backs off on 429, and is
fully resumable (a run that upgrades only part of the backlog is normal, not a
bug). If the key is missing or the project is denied, the step is skipped and
the pipeline continues on heuristic data.
"""

from __future__ import annotations

import logging
import os
import time

import httpx
from pydantic import BaseModel, ValidationError

log = logging.getLogger("jobradar")

MODEL = "gemini-2.5-flash"
ENDPOINT = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent"
MAX_PER_RUN = 40
MAX_RETRIES = 3

RESPONSE_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "summary": {"type": "STRING"},
        "salary_min": {"type": "INTEGER", "nullable": True},
        "salary_max": {"type": "INTEGER", "nullable": True},
        "salary_currency": {"type": "STRING", "nullable": True},
    },
    "required": ["summary"],
}

PROMPT = (
    "You extract structured data from a job posting. Return JSON only.\n"
    "- summary: one neutral sentence (max 160 chars) describing the role.\n"
    "- salary_min / salary_max: annual figures as integers if the text states a "
    "salary range or number, else null. Convert 'k' (e.g. 80k -> 80000). Do not invent.\n"
    "- salary_currency: ISO code (EUR, USD, GBP, ...) if a salary is present, else null.\n\n"
    "Posting:\n"
)


class LlmResult(BaseModel):
    summary: str
    salary_min: int | None = None
    salary_max: int | None = None
    salary_currency: str | None = None


class KeyDenied(Exception):
    """The API key is missing or the project is denied; skip LLM enrichment entirely."""


def _call(client: httpx.Client, api_key: str, prompt: str) -> tuple[LlmResult, int]:
    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "responseMimeType": "application/json",
            "responseSchema": RESPONSE_SCHEMA,
            "temperature": 0.1,
        },
    }
    for attempt in range(MAX_RETRIES):
        resp = client.post(ENDPOINT, params={"key": api_key}, json=body, timeout=45)
        if resp.status_code == 200:
            payload = resp.json()
            text = payload["candidates"][0]["content"]["parts"][0]["text"]
            tokens = payload.get("usageMetadata", {}).get("totalTokenCount", 0)
            return LlmResult.model_validate_json(text), tokens
        if resp.status_code in (401, 403):
            raise KeyDenied(f"{resp.status_code}: {resp.text[:120]}")
        if resp.status_code == 429:
            wait = 2 ** attempt * 5
            log.warning("gemini rate limited, backing off %ds", wait)
            time.sleep(wait)
            continue
        resp.raise_for_status()
    raise httpx.HTTPError("exhausted retries")


def _prompt_for(posting: dict) -> str:
    raw = posting.get("raw") or {}
    desc = (raw.get("description") or "")[:4000]
    return (
        f"{PROMPT}Title: {posting.get('title', '')}\n"
        f"Company: {posting.get('company', '')}\n"
        f"Location: {posting.get('location_raw', '')}\n"
        f"Description: {desc}\n"
    )


def enrich_with_llm(rows: list[dict]) -> tuple[list[dict], int]:
    """rows: [{posting_id, title, company, location_raw, raw}]. Returns (enrichment
    updates, tokens_used). Skips cleanly if the key is missing or denied."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        log.info("llm enrichment: no GEMINI_API_KEY, skipping")
        return [], 0

    updates: list[dict] = []
    tokens_total = 0
    with httpx.Client() as client:
        for posting in rows[:MAX_PER_RUN]:
            try:
                result, tokens = _call(client, api_key, _prompt_for(posting))
            except KeyDenied as exc:
                log.error("llm enrichment: key denied (%s); skipping LLM step", exc)
                break
            except (httpx.HTTPError, ValidationError, KeyError) as exc:
                log.warning("llm enrichment: posting %s failed: %s", posting["posting_id"], exc)
                continue
            tokens_total += tokens
            updates.append(
                {
                    "posting_id": posting["posting_id"],
                    "summary": result.summary[:200],
                    "salary_min": result.salary_min,
                    "salary_max": result.salary_max,
                    "salary_currency": result.salary_currency,
                    "model": MODEL,
                    "tokens": tokens,
                    "status": "ok",
                }
            )
    if updates:
        log.info("llm enrichment: upgraded %d postings, %d tokens", len(updates), tokens_total)
    return updates, tokens_total
