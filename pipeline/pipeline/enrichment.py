"""LLM enrichment layer.

Runs *after* the deterministic layer and upgrades heuristic rows with the two
things rules cannot do well: a one-line human summary and a salary parsed out of
prose. Region / remote / seniority / stack stay as the rule-based values.

The provider (Groq or Gemini) is chosen in providers.py by whichever key is set.
Designed around free-tier reality: bounded per run, backs off on 429, and fully
resumable. If no key is set or the key is denied, the step is skipped and the
pipeline continues on heuristic data.
"""

from __future__ import annotations

import logging

import httpx
from pydantic import ValidationError

from .providers import KeyDenied, select_provider

log = logging.getLogger("jobradar")

MAX_PER_RUN = 40

PROMPT = (
    "You extract structured data from a job posting. Return a JSON object with "
    "exactly these keys:\n"
    "- summary: one neutral sentence (max 160 chars) describing the role.\n"
    "- salary_min / salary_max: annual figures as integers if the text states a "
    "salary range or number, else null. Convert 'k' (e.g. 80k -> 80000). Do not invent.\n"
    "- salary_currency: ISO code (EUR, USD, GBP, ...) if a salary is present, else null.\n\n"
    "Posting:\n"
)


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
    updates, tokens_used). Skips cleanly if no provider is configured or denied."""
    provider = select_provider()
    if not provider:
        log.info("llm enrichment: no provider key set, skipping")
        return [], 0
    name, model, key, call = provider
    log.info("llm enrichment: using %s (%s)", name, model)

    updates: list[dict] = []
    tokens_total = 0
    with httpx.Client() as client:
        for posting in rows[:MAX_PER_RUN]:
            try:
                result, tokens = call(client, key, _prompt_for(posting))
            except KeyDenied as exc:
                log.error("llm enrichment: %s key denied (%s); skipping LLM step", name, exc)
                break
            except (httpx.HTTPError, ValidationError, KeyError, IndexError) as exc:
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
                    "model": model,
                    "tokens": tokens,
                    "status": "ok",
                }
            )
    if updates:
        log.info("llm enrichment: upgraded %d postings, %d tokens", len(updates), tokens_total)
    return updates, tokens_total
