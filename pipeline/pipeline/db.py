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


def enriched_posting_ids(client: Client) -> set[int]:
    """All posting ids that already have an enrichment row. Ids are cheap to page."""
    ids: set[int] = set()
    page = 0
    while True:
        rows = (
            client.table("enrichments")
            .select("posting_id")
            .range(page * 1000, page * 1000 + 999)
            .execute()
            .data
        )
        if not rows:
            break
        ids.update(row["posting_id"] for row in rows)
        if len(rows) < 1000:
            break
        page += 1
    return ids


def fetch_unenriched(client: Client, skip_ids: set[int], limit: int) -> list[dict]:
    """Postings that still need enrichment, oldest first, capped to bound run time."""
    collected: list[dict] = []
    page = 0
    while len(collected) < limit:
        rows = (
            client.table("postings")
            .select("id, title, company, location_raw, raw")
            .order("id")
            .range(page * INSERT_CHUNK, page * INSERT_CHUNK + INSERT_CHUNK - 1)
            .execute()
            .data
        )
        if not rows:
            break
        collected.extend(r for r in rows if r["id"] not in skip_ids)
        if len(rows) < INSERT_CHUNK:
            break
        page += 1
    return collected[:limit]


def fetch_for_llm(client: Client, limit: int) -> list[dict]:
    """Postings whose enrichment is still heuristic-only, flattened for the LLM step."""
    rows = (
        client.table("enrichments")
        .select("posting_id, postings(title, company, location_raw, raw)")
        .eq("status", "heuristic")
        .limit(limit)
        .execute()
        .data
    )
    out: list[dict] = []
    for row in rows:
        posting = row.get("postings") or {}
        out.append(
            {
                "posting_id": row["posting_id"],
                "title": posting.get("title", ""),
                "company": posting.get("company", ""),
                "location_raw": posting.get("location_raw", ""),
                "raw": posting.get("raw") or {},
            }
        )
    return out


def upsert_enrichments(client: Client, rows: list[dict]) -> int:
    written = 0
    for i in range(0, len(rows), INSERT_CHUNK):
        chunk = rows[i : i + INSERT_CHUNK]
        result = client.table("enrichments").upsert(chunk, on_conflict="posting_id").execute()
        written += len(result.data)
    return written
