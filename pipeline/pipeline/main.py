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

from . import db
from .config import load_env
from .models import RawPosting, RunMetrics, SourceResult
from .sources import ALL_SOURCES

log = logging.getLogger("jobradar")


async def fetch_all() -> list[SourceResult]:
    """Run every adapter; one failing source never takes down the run."""

    async def run_one(source) -> SourceResult:
        try:
            postings = await source.fetch()
            log.info("%-12s fetched %d postings", source.name, len(postings))
            return SourceResult(source=source.name, postings=postings)
        except Exception as exc:  # noqa: BLE001 - per-source isolation is the point
            log.error("%-12s FAILED: %s", source.name, exc)
            return SourceResult(source=source.name, error=str(exc))

    return list(await asyncio.gather(*(run_one(s) for s in ALL_SOURCES)))


def dedupe_batch(results: list[SourceResult]) -> list[RawPosting]:
    """Cross-source dedupe within this run; first source wins."""
    seen: set[str] = set()
    unique: list[RawPosting] = []
    for result in results:
        for posting in result.postings:
            if posting.hash in seen:
                continue
            seen.add(posting.hash)
            unique.append(posting)
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
    metrics.finished_at = datetime.now(timezone.utc)
    db.record_run(client, metrics)

    _print_summary(metrics, fresh, dry_run=False)
    return 0 if not failed_sources else 1


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
