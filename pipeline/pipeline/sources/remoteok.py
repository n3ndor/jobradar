"""RemoteOK public API. https://remoteok.com/api

Per RemoteOK's terms, usage requires a visible link back to remoteok.com; the
dashboard footer and every posting's source badge honor that. The first element
of the response is a legal/metadata notice, not a job, so it is skipped.
"""

from __future__ import annotations

from datetime import datetime

import httpx

from ..models import RawPosting

API_URL = "https://remoteok.com/api"


class RemoteOkSource:
    name = "remoteok"

    async def fetch(self) -> list[RawPosting]:
        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            resp = await client.get(API_URL, headers={"User-Agent": "jobradar-pipeline"})
            resp.raise_for_status()
            data = resp.json()

        postings: list[RawPosting] = []
        for job in data:
            # Skip the leading notice object and anything without the core fields.
            if not job.get("id") or not job.get("position") or not job.get("company"):
                continue
            postings.append(
                RawPosting(
                    source=self.name,
                    external_id=str(job["id"]),
                    company=job["company"],
                    title=job["position"],
                    url=job["url"],
                    location_raw=job.get("location") or "Remote",
                    posted_at=_parse_date(job.get("date")),
                    raw={
                        "tags": job.get("tags", []),
                        "description": _slim(job.get("description", "")),
                    },
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


def _slim(html: str) -> str:
    return (html or "")[:8000]
