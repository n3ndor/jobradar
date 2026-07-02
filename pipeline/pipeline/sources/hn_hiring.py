"""Hacker News "Ask HN: Who is hiring?" via the Algolia API.

Each month HN runs one hiring thread; its top-level comments are job posts in a
loose "Company | Role | Location | REMOTE | url" convention. We find the latest
thread, then parse the comments defensively: only comments that look structured
(a pipe-delimited header) become postings, so freeform replies are ignored.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone

import httpx

SEARCH_URL = "https://hn.algolia.com/api/v1/search_by_date"
ITEM_URL = "https://hn.algolia.com/api/v1/items/{id}"

TAG_RE = re.compile(r"<[^>]+>")
HREF_RE = re.compile(r'href="([^"]+)"')
ROLE_HINT = re.compile(
    r"engineer|developer|scientist|designer|devops|sre|architect|manager|"
    r"programmer|analyst|lead|full.?stack|frontend|backend|data|security|ml|ai",
    re.IGNORECASE,
)


class HackerNewsSource:
    name = "hackernews"

    async def fetch(self):
        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            search = await client.get(
                SEARCH_URL,
                params={"query": "Ask HN: Who is hiring", "tags": "story", "hitsPerPage": 20},
                headers={"User-Agent": "jobradar-pipeline"},
            )
            search.raise_for_status()
            thread = _latest_hiring_thread(search.json().get("hits", []))
            if not thread:
                return []

            item = await client.get(
                ITEM_URL.format(id=thread["objectID"]),
                headers={"User-Agent": "jobradar-pipeline"},
            )
            item.raise_for_status()
            children = item.json().get("children", [])

        from ..models import RawPosting

        postings: list[RawPosting] = []
        for comment in children:
            parsed = _parse_comment(comment)
            if not parsed:
                continue
            company, title, location, url = parsed
            postings.append(
                RawPosting(
                    source=self.name,
                    external_id=str(comment["id"]),
                    company=company,
                    title=title,
                    url=url,
                    location_raw=location,
                    posted_at=_parse_date(comment.get("created_at")),
                    raw={"description": _strip(comment.get("text", ""))[:8000], "hn_thread": thread["title"]},
                )
            )
        return postings


def _latest_hiring_thread(hits: list[dict]) -> dict | None:
    """Pick the real monthly thread: title starts with 'Ask HN: Who is hiring'
    and, among matches, the one with the most comments (guards against reposts,
    'Show HN' plugins, and empty threads that merely mention the phrase)."""
    matches = [
        h for h in hits if h.get("title", "").lower().startswith("ask hn: who is hiring")
    ]
    if not matches:
        return None
    return max(matches, key=lambda h: h.get("num_comments") or 0)


def _parse_comment(comment: dict) -> tuple[str, str, str, str] | None:
    text = comment.get("text") or ""
    if not text:
        return None
    header = _strip(text.split("<p>")[0])
    segments = [s.strip() for s in header.split("|") if s.strip()]
    if len(segments) < 2:
        return None  # not the structured hiring format

    # Only accept comments where a segment clearly names a role; otherwise the
    # "title" would just be a location or a tagline. Quality over volume.
    role = next((s for s in segments[1:] if ROLE_HINT.search(s)), None)
    if not role:
        return None

    company = segments[0][:80]
    title = role[:120]
    location = next(
        (s for s in segments if s != role and re.search(r"remote|onsite|hybrid|,", s, re.IGNORECASE)),
        "",
    )[:80]

    fallback = f"https://news.ycombinator.com/item?id={comment['id']}"
    href = HREF_RE.search(text)
    url = _decode(href.group(1)) if href else fallback
    if not url.startswith("http"):
        url = fallback
    return company, title, location, url


def _parse_date(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)
    except ValueError:
        return None


def _decode(text: str) -> str:
    for a, b in (("&amp;", "&"), ("&lt;", "<"), ("&gt;", ">"), ("&#x27;", "'"), ("&#x2F;", "/"), ("&quot;", '"')):
        text = text.replace(a, b)
    return text


def _strip(html: str) -> str:
    return re.sub(r"\s+", " ", _decode(TAG_RE.sub(" ", html))).strip()
