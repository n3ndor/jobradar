"""Thin Supabase wrapper: the pipeline needs exactly four operations, no ORM."""

from __future__ import annotations

from datetime import datetime, timezone

from supabase import Client, create_client

from .config import require
from .models import RawPosting, RunMetrics

INSERT_CHUNK = 200


def connect() -> Client:
    return create_client(require("SUPABASE_URL"), require("SUPABASE_SECRET_KEY"))


def ensure_sources(client: Client, names: list[str]) -> dict[str, int]:
    """Return {source_name: id}, creating rows for sources seen for the first time."""
    existing = client.table("sources").select("id, name").execute().data
    ids = {row["name"]: row["id"] for row in existing}
    missing = [n for n in names if n not in ids]
    if missing:
        created = (
            client.table("sources")
            .insert([{"name": n, "kind": "api"} for n in missing])
            .execute()
            .data
        )
        ids.update({row["name"]: row["id"] for row in created})
    return ids


def existing_hashes(client: Client, hashes: list[str]) -> set[str]:
    """Which of these dedupe hashes are already stored? Chunked to stay under URL limits."""
    found: set[str] = set()
    for i in range(0, len(hashes), INSERT_CHUNK):
        chunk = hashes[i : i + INSERT_CHUNK]
        rows = client.table("postings").select("hash").in_("hash", chunk).execute().data
        found.update(row["hash"] for row in rows)
    return found


def insert_postings(client: Client, postings: list[RawPosting], source_ids: dict[str, int]) -> int:
    inserted = 0
    for i in range(0, len(postings), INSERT_CHUNK):
        chunk = postings[i : i + INSERT_CHUNK]
        rows = [p.to_row(source_ids[p.source]) for p in chunk]
        result = client.table("postings").upsert(rows, on_conflict="hash", ignore_duplicates=True).execute()
        inserted += len(result.data)
    return inserted


def mark_source_run(client: Client, source_ids: dict[str, int], names: list[str]) -> None:
    now = datetime.now(timezone.utc).isoformat()
    for name in names:
        client.table("sources").update({"last_run_at": now}).eq("id", source_ids[name]).execute()


def record_run(client: Client, metrics: RunMetrics) -> None:
    client.table("pipeline_runs").insert(metrics.to_row()).execute()
