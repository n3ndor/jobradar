import httpx
import respx

from pipeline.sources.arbeitnow import ArbeitnowSource
from pipeline.sources.greenhouse import GreenhouseSource
from pipeline.sources.hn_hiring import HackerNewsSource
from pipeline.sources.remoteok import RemoteOkSource
from pipeline.sources.remotive import RemotiveSource
from pipeline.sources.wwr import WeWorkRemotelySource


async def test_remotive_parses_jobs():
    with respx.mock(assert_all_called=False) as router:
        router.get("https://remotive.com/api/remote-jobs").mock(
            return_value=httpx.Response(
                200,
                json={
                    "jobs": [
                        {
                            "id": 1,
                            "title": "Backend Engineer",
                            "company_name": "Acme",
                            "url": "https://example.com/1",
                            "candidate_required_location": "Remote",
                            "publication_date": "2026-01-01T00:00:00",
                        },
                        {"id": 2, "title": "", "company_name": "NoTitle"},  # skipped
                    ]
                },
            )
        )
        postings = await RemotiveSource().fetch()

    assert len(postings) == 1
    assert postings[0].company == "Acme"
    assert postings[0].source == "remotive"


async def test_arbeitnow_parses_and_marks_remote(monkeypatch):
    monkeypatch.setattr("pipeline.sources.arbeitnow.MAX_PAGES", 1)
    with respx.mock(assert_all_called=False) as router:
        router.route(method="GET", host="www.arbeitnow.com", path="/api/job-board-api").mock(
            return_value=httpx.Response(
                200,
                json={
                    "data": [
                        {
                            "slug": "abc",
                            "title": "Software Engineer",
                            "company_name": "Beispiel GmbH",
                            "url": "https://example.com/abc",
                            "location": "Berlin",
                            "remote": True,
                            "created_at": 1700000000,
                        }
                    ]
                },
            )
        )
        postings = await ArbeitnowSource().fetch()

    assert postings[0].external_id == "abc"
    assert "remote" in postings[0].location_raw.lower()


async def test_greenhouse_filters_non_tech_and_strips_html(monkeypatch):
    monkeypatch.setattr("pipeline.sources.greenhouse.BOARDS", ["acme"])
    with respx.mock(assert_all_called=False) as router:
        router.route(method="GET", host="boards-api.greenhouse.io", path="/v1/boards/acme/jobs").mock(
            return_value=httpx.Response(
                200,
                json={
                    "jobs": [
                        {
                            "id": 1,
                            "title": "Senior Software Engineer",
                            "company_name": "Acme",
                            "absolute_url": "https://example.com/1",
                            "location": {"name": "Remote, US"},
                            "first_published": "2026-01-01T00:00:00+00:00",
                            "content": "<p>We use Python &amp; Go</p>",
                            "departments": [{"name": "Engineering"}],
                        },
                        {
                            "id": 2,
                            "title": "Account Executive",
                            "company_name": "Acme",
                            "absolute_url": "https://example.com/2",
                            "location": {"name": "NYC"},
                            "content": "",
                        },
                    ]
                },
            )
        )
        postings = await GreenhouseSource().fetch()

    titles = [p.title for p in postings]
    assert "Senior Software Engineer" in titles
    assert "Account Executive" not in titles  # adapter's tech-title filter
    assert "<p>" not in postings[0].raw["description"]
    assert "&" in postings[0].raw["description"]  # entity decoded


async def test_remoteok_skips_notice_and_defaults_remote():
    with respx.mock(assert_all_called=False) as router:
        router.get("https://remoteok.com/api").mock(
            return_value=httpx.Response(
                200,
                json=[
                    {"legal": "notice, not a job"},
                    {
                        "id": "1",
                        "position": "Backend Engineer",
                        "company": "Acme",
                        "url": "https://example.com/1",
                        "location": "",
                        "date": "2026-01-01T00:00:00+00:00",
                        "tags": ["dev"],
                        "description": "desc",
                    },
                ],
            )
        )
        postings = await RemoteOkSource().fetch()

    assert len(postings) == 1
    assert postings[0].location_raw == "Remote"  # empty location -> Remote


WWR_RSS = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel>
  <item>
    <title>Acme: Senior Engineer</title>
    <link>https://weworkremotely.com/remote-jobs/acme-senior-engineer</link>
    <region>Remote</region>
    <description>&lt;p&gt;URL: &lt;a href="http://acme.com"&gt;acme&lt;/a&gt;&lt;/p&gt;</description>
    <pubDate>Mon, 01 Jan 2026 00:00:00 +0000</pubDate>
  </item>
</channel></rss>"""


async def test_wwr_parses_rss(monkeypatch):
    monkeypatch.setattr(
        "pipeline.sources.wwr.FEEDS", ["https://weworkremotely.com/feed.rss"]
    )
    with respx.mock(assert_all_called=False) as router:
        router.get("https://weworkremotely.com/feed.rss").mock(
            return_value=httpx.Response(200, text=WWR_RSS)
        )
        postings = await WeWorkRemotelySource().fetch()

    assert postings[0].company == "Acme"
    assert postings[0].title == "Senior Engineer"


async def test_hackernews_parses_structured_comments_only():
    search = {
        "hits": [
            {"objectID": "100", "title": "Ask HN: Who is hiring? (July 2026)", "num_comments": 200},
            {"objectID": "999", "title": "Show HN: a plugin", "num_comments": 5},
        ]
    }
    item = {
        "children": [
            {
                "id": 1,
                "created_at": "2026-07-01T00:00:00Z",
                "text": 'Acme | Senior Backend Engineer | Berlin | REMOTE | '
                '<a href="https:&#x2F;&#x2F;acme.com">acme</a>',
            },
            {"id": 2, "created_at": "2026-07-01T00:00:00Z", "text": "just a reply, no structure"},
        ]
    }
    with respx.mock(assert_all_called=False) as router:
        router.route(method="GET", host="hn.algolia.com", path="/api/v1/search_by_date").mock(
            return_value=httpx.Response(200, json=search)
        )
        router.route(method="GET", host="hn.algolia.com", path="/api/v1/items/100").mock(
            return_value=httpx.Response(200, json=item)
        )
        postings = await HackerNewsSource().fetch()

    assert len(postings) == 1  # unstructured reply skipped
    p = postings[0]
    assert p.company == "Acme"
    assert "Backend Engineer" in p.title
    assert "acme.com" in str(p.url)  # entity-decoded URL
    assert "&#x2F;" not in str(p.url)
