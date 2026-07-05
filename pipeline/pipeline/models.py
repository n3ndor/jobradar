"""Models: postings and per-source results come from jobfeeds, the package
extracted from this pipeline. JobRadar adds only what the product needs on
top: the database row mapping and run metrics."""

from __future__ import annotations

from datetime import datetime, timezone

from jobfeeds import Posting as RawPosting, SourceResult, posting_hash
from pydantic import BaseModel, Field

__all__ = ["RawPosting", "SourceResult", "posting_hash", "posting_row", "RunMetrics"]


def posting_row(posting: RawPosting, source_id: int) -> dict:
    """Map a jobfeeds Posting onto the postings table schema."""
    return {
        "source_id": source_id,
        "external_id": posting.external_id,
        "hash": posting.hash,
        "company": posting.company,
        "title": posting.title,
        "url": str(posting.url),
        "location_raw": posting.location_raw,
        "posted_at": posting.posted_at.isoformat() if posting.posted_at else None,
        "raw": posting.raw,
    }


class RunMetrics(BaseModel):
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    finished_at: datetime | None = None
    fetched: int = 0
    new_postings: int = 0
    enriched: int = 0
    failed: int = 0
    tokens_used: int = 0
    notes: str = ""

    @property
    def duration_s(self) -> float:
        end = self.finished_at or datetime.now(timezone.utc)
        return round((end - self.started_at).total_seconds(), 2)

    def to_row(self) -> dict:
        return {
            "started_at": self.started_at.isoformat(),
            "finished_at": (self.finished_at or datetime.now(timezone.utc)).isoformat(),
            "fetched": self.fetched,
            "new_postings": self.new_postings,
            "enriched": self.enriched,
            "failed": self.failed,
            "tokens_used": self.tokens_used,
            "duration_s": self.duration_s,
            "notes": self.notes,
        }
