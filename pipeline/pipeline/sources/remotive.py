"""Remotive public API adapter. https://remotive.com/api/remote-jobs"""

from __future__ import annotations

from datetime import datetime

import httpx

from ..models import RawPosting

API_URL = "https://remotive.com/api/remote-jobs"


class RemotiveSource:
    name = "remotive"

    async def fetch(self) -> list[RawPosting]:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(API_URL, headers={"User-Agent": "jobradar-pipeline"})
            resp.raise_for_status()
            jobs = resp.json().get("jobs", [])

        postings: list[RawPosting] = []
        for job in jobs:
            if not job.get("title") or not job.get("company_name"):
                continue
            postings.append(
                RawPosting(
                    source=self.name,
                    external_id=str(job["id"]),
                    company=job["company_name"],
                    title=job["title"],
                    url=job["url"],
                    location_raw=job.get("candidate_required_location", ""),
                    posted_at=_parse_date(job.get("publication_date")),
                    raw=_slim(job),
                )
            )
        return postings


def _parse_date(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def _slim(job: dict) -> dict:
    """Keep the raw payload useful but bounded: description is by far the largest field."""
    slim = dict(job)
    desc = slim.get("description") or ""
    slim["description"] = desc[:8000]
    return slim
