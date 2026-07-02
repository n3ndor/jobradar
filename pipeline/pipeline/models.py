"""Pydantic models shared across the pipeline."""

from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone

from pydantic import BaseModel, Field, HttpUrl


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().lower()


def posting_hash(company: str, title: str, location_raw: str) -> str:
    """Cross-source dedupe key: same company + title + normalized location."""
    key = "|".join((_normalize(company), _normalize(title), _normalize(location_raw)))
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


class RawPosting(BaseModel):
    source: str
    external_id: str
    company: str
    title: str
    url: HttpUrl
    location_raw: str = ""
    posted_at: datetime | None = None
    raw: dict = Field(default_factory=dict)

    @property
    def hash(self) -> str:
        return posting_hash(self.company, self.title, self.location_raw)

    def to_row(self, source_id: int) -> dict:
        return {
            "source_id": source_id,
            "external_id": self.external_id,
            "hash": self.hash,
            "company": self.company,
            "title": self.title,
            "url": str(self.url),
            "location_raw": self.location_raw,
            "posted_at": self.posted_at.isoformat() if self.posted_at else None,
            "raw": self.raw,
        }


class SourceResult(BaseModel):
    """Outcome of one adapter's fetch, success or failure."""

    source: str
    postings: list[RawPosting] = Field(default_factory=list)
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.error is None


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
