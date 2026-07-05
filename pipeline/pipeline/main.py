"""Pipeline entry point: fetch all sources concurrently, dedupe, store, record the run.

Usage:
    python -m pipeline.main            # full run (requires SUPABASE_URL + SUPABASE_SECRET_KEY)
    python -m pipeline.main --dry-run  # fetch + dedupe in memory, print summary, no DB
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from datetime import datetime, timezone

import jobfeeds

from . import db, enrich_rules
from .config import load_env
from .enrichment import MAX_PER_RUN as LLM_PER_RUN, enrich_with_llm
from .models import RawPosting, RunMetrics, SourceResult
from .sources import ALL_SOURCES
from .tech_filter import is_tech_role

log = logging.getLogger("jobradar")

# Cap heuristic backfill per run so a large first-time backlog spreads over a few
# runs instead of one very long job. Well above a normal run's new-posting count.
ENRICH_LIMIT = 1500


async def fetch_all() -> list[SourceResult]:
    """Fetch every source via jobfeeds (our own OSS package); failure
    isolation lives in the package, this wrapper only adds logging."""
    results = await jobfeeds.fetch_all(ALL_SOURCES)
    for r in results:
        if r.ok:
            log.info("%-12s fetched %d postings", r.source, len(r.postings))
        else:
            log.error("%-12s FAILED: %s", r.source, r.error)
    return results


def dedupe_batch(results: list[SourceResult]) -> list[RawPosting]:
    """Tech-role gate + cross-source dedupe within this run; first source wins."""
    seen: set[str] = set()
    unique: list[RawPosting] = []
    dropped = 0
    for result in results:
        for posting in result.postings:
            if not is_tech_role(posting.title):
                dropped += 1
                continue
            if posting.hash in seen:
                continue
            seen.add(posting.hash)
            unique.append(posting)
    if dropped:
        log.info("tech filter: dropped %d non-tech postings", dropped)
    return unique


async def run(dry_run: bool) -> int:
    metrics = RunMetrics()
    results = await fetch_all()
    metrics.fetched = sum(len(r.postings) for r in results)
    failed_sources = [r.source for r in results if not r.ok]
    if failed_sources:
        metrics.notes = f"source errors: {', '.join(failed_sources)}"

    unique = dedupe_batch(results)
    log.info("batch: %d fetched, %d unique after in-run dedupe", metrics.fetched, len(unique))

    if dry_run:
        log.info("dry run: skipping database writes")
        _print_summary(metrics, unique, dry_run=True)
        return 0 if not failed_sources else 1

    client = db.connect()
    source_ids = db.ensure_sources(client, [s.name for s in ALL_SOURCES])
    known = db.existing_hashes(client, [p.hash for p in unique])
    fresh = [p for p in unique if p.hash not in known]
    metrics.new_postings = db.insert_postings(client, fresh, source_ids)
    db.mark_source_run(client, source_ids, [r.source for r in results if r.ok])

    metrics.enriched = enrich_pending(client)
    metrics.tokens_used = llm_enrich_pending(client)

    metrics.finished_at = datetime.now(timezone.utc)
    db.record_run(client, metrics)

    _print_summary(metrics, fresh, dry_run=False)
    return 0 if not failed_sources else 1


def enrich_pending(client) -> int:
    """Rule-based enrichment for every posting that lacks an enrichment row."""
    skip = db.enriched_posting_ids(client)
    pending = db.fetch_unenriched(client, skip, ENRICH_LIMIT)
    if not pending:
        log.info("enrichment: nothing pending")
        return 0
    rows = [{"posting_id": p["id"], **enrich_rules.classify(p)} for p in pending]
    written = db.upsert_enrichments(client, rows)
    log.info("enrichment: %d postings enriched (rules)", written)
    return written


def llm_enrich_pending(client) -> int:
    """Upgrade a bounded batch of heuristic rows with LLM summary + salary. Returns
    tokens spent. No-op (and never fatal) when the Gemini key is absent or denied."""
    candidates = db.fetch_for_llm(client, LLM_PER_RUN)
    if not candidates:
        return 0
    try:
        updates, tokens = enrich_with_llm(candidates)
    except Exception as exc:  # noqa: BLE001 - LLM must never break the ingest run
        log.error("llm enrichment: unexpected error, continuing on heuristics: %s", exc)
        return 0
    if updates:
        db.upsert_enrichments(client, updates)
    return tokens


def _print_summary(metrics: RunMetrics, new: list[RawPosting], dry_run: bool) -> None:
    mode = "DRY RUN" if dry_run else "RUN"
    log.info(
        "%s complete: fetched=%d new=%d duration=%.1fs %s",
        mode, metrics.fetched, len(new), metrics.duration_s,
        f"({metrics.notes})" if metrics.notes else "",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="JobRadar ingestion pipeline")
    parser.add_argument("--dry-run", action="store_true", help="fetch and dedupe only, no database writes")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-7s %(message)s")
    load_env()
    sys.exit(asyncio.run(run(dry_run=args.dry_run)))


if __name__ == "__main__":
    main()
