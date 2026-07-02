"""Greenhouse public job board API. https://developers.greenhouse.io/job-board.html

Greenhouse hosts real, direct-employer postings for a lot of well-known tech
companies. There is no global search endpoint, so we curate a list of board
tokens (the company slug in boards.greenhouse.io/<token>). Because these boards
are large and mostly non-engineering, we keep only tech-role titles and cap the
count per company so one big board cannot dominate the feed.
"""

from __future__ import annotations

import asyncio
import re
from datetime import datetime

import httpx

from ..models import RawPosting

# Verified live boards (probed against the API). Add tokens here to widen coverage.
BOARDS = [
    "stripe", "airbnb", "gitlab", "figma", "databricks", "reddit", "dropbox",
    "coinbase", "robinhood", "instacart", "discord", "asana", "brex", "vercel",
    "anthropic", "cloudflare", "gusto", "samsara", "affirm",
]

PER_BOARD_LIMIT = 40
CONCURRENCY = 6

TECH_TITLE = re.compile(
    r"\b("
    r"engineer|developer|software|programmer|sre|devops|"
    r"data\s*(scientist|engineer|analyst)|machine\s*learning|ml\b|ai\b|"
    r"backend|back-end|frontend|front-end|full\s*stack|fullstack|"
    r"infrastructure|platform|security|cloud|mobile|ios|android|"
    r"designer|design\b|product\s*manager|architect|qa\b|"
    r"analytics|scientist|research"
    r")",
    re.IGNORECASE,
)
TAG_RE = re.compile(r"<[^>]+>")


class GreenhouseSource:
    name = "greenhouse"

    async def fetch(self) -> list[RawPosting]:
        sem = asyncio.Semaphore(CONCURRENCY)
        async with httpx.AsyncClient(timeout=30) as client:
            batches = await asyncio.gather(
                *(self._fetch_board(client, sem, token) for token in BOARDS),
                return_exceptions=True,
            )
        postings: list[RawPosting] = []
        for batch in batches:
            if isinstance(batch, list):
                postings.extend(batch)
        return postings

    async def _fetch_board(
        self, client: httpx.AsyncClient, sem: asyncio.Semaphore, token: str
    ) -> list[RawPosting]:
        async with sem:
            resp = await client.get(
                f"https://boards-api.greenhouse.io/v1/boards/{token}/jobs",
                params={"content": "true"},
                headers={"User-Agent": "jobradar-pipeline"},
            )
            resp.raise_for_status()
            jobs = resp.json().get("jobs", [])

        tech = [j for j in jobs if TECH_TITLE.search(j.get("title", ""))]
        tech.sort(key=lambda j: j.get("updated_at") or "", reverse=True)

        postings: list[RawPosting] = []
        for job in tech[:PER_BOARD_LIMIT]:
            url = job.get("absolute_url")
            title = job.get("title")
            if not url or not title:
                continue
            postings.append(
                RawPosting(
                    source=self.name,
                    external_id=str(job["id"]),
                    company=job.get("company_name") or token.title(),
                    title=title,
                    url=url,
                    location_raw=(job.get("location") or {}).get("name", ""),
                    posted_at=_parse_date(job.get("first_published") or job.get("updated_at")),
                    raw={
                        "board": token,
                        "departments": [d.get("name") for d in job.get("departments", [])],
                        "description": _strip_html(job.get("content", ""))[:8000],
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


def _strip_html(html: str) -> str:
    text = TAG_RE.sub(" ", html)
    text = (
        text.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
        .replace("&#39;", "'").replace("&quot;", '"').replace("&nbsp;", " ")
    )
    return re.sub(r"\s+", " ", text).strip()
