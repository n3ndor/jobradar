"""Job sources come from jobfeeds (pip install jobfeeds), the open-source
package extracted from this very pipeline: github.com/n3ndor/jobfeeds

What stays here is JobRadar product policy, not feed access:
- which Greenhouse boards we watch
- the tech-role title filter applied at the Greenhouse fetch (so the
  per-board cap is spent on tech roles, not sales listings)
"""

from __future__ import annotations

from jobfeeds import (
    Arbeitnow,
    Greenhouse,
    HNWhoIsHiring,
    RemoteOK,
    Remotive,
    WeWorkRemotely,
)

from .tech_filter import TECH_TITLE

# Verified live boards (probed against the API). Add tokens here to widen coverage.
BOARDS = [
    "stripe", "airbnb", "gitlab", "figma", "databricks", "reddit", "dropbox",
    "coinbase", "robinhood", "instacart", "discord", "asana", "brex", "vercel",
    "anthropic", "cloudflare", "gusto", "samsara", "affirm",
]

ALL_SOURCES = [
    Remotive(),
    Arbeitnow(),
    Greenhouse(boards=BOARDS, title_pattern=TECH_TITLE),
    RemoteOK(),
    WeWorkRemotely(),
    HNWhoIsHiring(),
]
