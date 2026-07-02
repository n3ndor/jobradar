"""Arbeitnow public job board API adapter (DACH-focused). https://www.arbeitnow.com/api/job-board-api"""

from __future__ import annotations

from datetime import datetime, timezone

import httpx

from ..models import RawPosting

API_URL = "https://www.arbeitnow.com/api/job-board-api"
MAX_PAGES = 3


class ArbeitnowSource:
    name = "arbeitnow"

    async def fetch(self) -> list[RawPosting]:
        postings: list[RawPosting] = []
        async with httpx.AsyncClient(timeout=30) as client:
            # links.next in this API sometimes points at filtered views, so paginate explicitly
            for page in range(1, MAX_PAGES + 1):
                resp = await client.get(
                    API_URL, params={"page": page}, headers={"User-Agent": "jobradar-pipeline"}
                )
                resp.raise_for_status()
                payload = resp.json()
                data = payload.get("data", [])
                if not data:
                    break
                for job in data:
                    if not job.get("title") or not job.get("company_name"):
                        continue
                    postings.append(
                        RawPosting(
                            source=self.name,
                            external_id=job["slug"],
                            company=job["company_name"],
                            title=job["title"],
                            url=job["url"],
                            location_raw=_location(job),
                            posted_at=_from_unix(job.get("created_at")),
                            raw=_slim(job),
                        )
                    )
        return postings


def _location(job: dict) -> str:
    loc = job.get("location") or ""
    if job.get("remote"):
        return f"{loc} (remote)" if loc else "Remote"
    return loc


def _from_unix(value: int | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromtimestamp(value, tz=timezone.utc)


def _slim(job: dict) -> dict:
    slim = dict(job)
    desc = slim.get("description") or ""
    slim["description"] = desc[:8000]
    return slim
