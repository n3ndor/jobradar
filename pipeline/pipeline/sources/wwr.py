"""We Work Remotely RSS feeds. https://weworkremotely.com

WWR publishes one RSS feed per category. We pull the tech-relevant categories;
item titles follow a "Company: Role" convention, and the description carries the
canonical URL and body.
"""

from __future__ import annotations

import re
from datetime import datetime
from email.utils import parsedate_to_datetime
from xml.etree import ElementTree

import httpx

from ..models import RawPosting

FEEDS = [
    "https://weworkremotely.com/categories/remote-programming-jobs.rss",
    "https://weworkremotely.com/categories/remote-devops-sysadmin-jobs.rss",
    "https://weworkremotely.com/categories/remote-design-jobs.rss",
    "https://weworkremotely.com/categories/remote-product-jobs.rss",
]

TAG_RE = re.compile(r"<[^>]+>")
URL_IN_DESC = re.compile(r'URL:\s*<a[^>]*href="([^"]+)"', re.IGNORECASE)


class WeWorkRemotelySource:
    name = "weworkremotely"

    async def fetch(self) -> list[RawPosting]:
        postings: list[RawPosting] = []
        seen: set[str] = set()
        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            for feed in FEEDS:
                resp = await client.get(feed, headers={"User-Agent": "jobradar-pipeline"})
                resp.raise_for_status()
                for posting in self._parse(resp.text):
                    if posting.external_id in seen:
                        continue
                    seen.add(posting.external_id)
                    postings.append(posting)
        return postings

    def _parse(self, xml: str) -> list[RawPosting]:
        root = ElementTree.fromstring(xml)
        out: list[RawPosting] = []
        for item in root.iter("item"):
            title = (item.findtext("title") or "").strip()
            link = (item.findtext("link") or "").strip()
            if not title or not link:
                continue
            company, _, role = title.partition(":")
            company, role = company.strip(), role.strip()
            if not role:
                company, role = "", company
            region = (item.findtext("region") or "").strip()
            desc = item.findtext("description") or ""
            out.append(
                RawPosting(
                    source=self.name,
                    external_id=link.rstrip("/").rsplit("/", 1)[-1] or link,
                    company=company or "Unknown",
                    title=role,
                    url=link,
                    location_raw=region or "Remote",
                    posted_at=_parse_date(item.findtext("pubDate")),
                    raw={"description": _strip(desc)[:8000]},
                )
            )
        return out


def _parse_date(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return parsedate_to_datetime(value)
    except (TypeError, ValueError):
        return None


def _strip(html: str) -> str:
    return re.sub(r"\s+", " ", TAG_RE.sub(" ", html)).strip()
