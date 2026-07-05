"""The adapters themselves are tested in the jobfeeds package
(github.com/n3ndor/jobfeeds); what JobRadar owns is their configuration."""

from jobfeeds import Greenhouse

from pipeline.sources import ALL_SOURCES, BOARDS
from pipeline.tech_filter import TECH_TITLE


def test_all_six_sources_configured():
    names = [s.name for s in ALL_SOURCES]
    assert names == [
        "remotive",
        "arbeitnow",
        "greenhouse",
        "remoteok",
        "weworkremotely",
        "hackernews",
    ]


def test_greenhouse_gets_product_policy():
    gh = next(s for s in ALL_SOURCES if isinstance(s, Greenhouse))
    assert gh.boards == BOARDS
    # The tech filter runs at fetch so the per-board cap is spent on tech
    # roles; dedupe_batch applies the same filter to every other source.
    assert gh.title_pattern is TECH_TITLE
    assert gh.title_pattern.search("Senior Software Engineer")
    assert not gh.title_pattern.search("Account Executive")
