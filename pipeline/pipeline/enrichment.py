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

from .providers import REGIONS, REMOTE_POLICIES, KeyDenied, LlmResult, select_provider

log = logging.getLogger("jobradar")

MAX_PER_RUN = 40


def llm_update_row(posting: dict, result: LlmResult, model: str, tokens: int) -> dict:
    """Build the enrichments upsert row from an LLM result. The LLM's remote/region
    verdict overrides the heuristic one (it read the full description; the rules only
    saw the location field). When the LLM abstains, the heuristic values stay, so
    every row carries the same keys (bulk upsert requires uniform columns)."""
    remote_policy = posting.get("remote_policy")
    if result.remote_policy in REMOTE_POLICIES and result.remote_policy != "unknown":
        remote_policy = result.remote_policy
    region = posting.get("region")
    if result.region in REGIONS:
        region = result.region

    if region:
        # Reachable from DACH: located there, or fully remote without a
        # region lock that excludes Europe.
        dach_friendly = region == "DACH" or (
            remote_policy == "remote" and region in ("Global / Remote", "Europe")
        )
    else:
        dach_friendly = posting.get("dach_friendly")

    return {
        "posting_id": posting["posting_id"],
        "summary": result.summary[:200],
        "salary_min": result.salary_min,
        "salary_max": result.salary_max,
        "salary_currency": result.salary_currency,
        "remote_policy": remote_policy,
        "region": region,
        "dach_friendly": dach_friendly,
        "model": model,
        "tokens": tokens,
        "status": "ok",
    }

PROMPT = (
    "You extract structured data from a job posting. Return a JSON object with "
    "exactly these keys:\n"
    "- summary: one neutral sentence (max 160 chars) describing the role.\n"
    "- salary_min / salary_max: annual figures as integers if the text states a "
    "salary range or number, else null. Convert 'k' (e.g. 80k -> 80000). Do not invent.\n"
    "- salary_currency: ISO code (EUR, USD, GBP, ...) if a salary is present, else null.\n"
    "- remote_policy: one of remote|hybrid|onsite|unknown. Judge from the FULL "
    "description, not just the location field; job boards often flag postings as "
    "remote when the text says otherwise. German phrases like 'an unseren "
    "Standorten', 'vor Ort', 'im Büro' mean onsite; 'Available Locations: <city>' "
    "without remote wording means onsite; hybrid means some office days required. "
    "Only answer remote if the text clearly allows working fully remotely.\n"
    "- region: one of DACH|UK & Ireland|Europe|US|Canada|APAC|LATAM|"
    "Global / Remote|Other. The region where the job or its eligible candidates "
    "are located (DACH = Germany/Austria/Switzerland). Use Global / Remote only "
    "for fully remote roles without a country or region restriction.\n\n"
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
            updates.append(llm_update_row(posting, result, model, tokens))
    if updates:
        log.info("llm enrichment: upgraded %d postings, %d tokens", len(updates), tokens_total)
    return updates, tokens_total
