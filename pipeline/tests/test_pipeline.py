from pipeline.main import dedupe_batch
from pipeline.models import RawPosting, SourceResult


def _posting(source, title, company="Acme", location="Remote", ext="x"):
    return RawPosting(
        source=source,
        external_id=ext,
        company=company,
        title=title,
        url="https://example.com/x",
        location_raw=location,
    )


def test_dedupe_batch_drops_non_tech():
    results = [
        SourceResult(source="a", postings=[_posting("a", "Software Engineer")]),
        SourceResult(source="a", postings=[_posting("a", "Account Executive")]),
    ]
    unique = dedupe_batch(results)
    titles = [p.title for p in unique]
    assert "Software Engineer" in titles
    assert "Account Executive" not in titles


def test_dedupe_batch_deduplicates_across_sources():
    # Same company+title+location from two sources collapses to one; first wins.
    p1 = _posting("remotive", "Backend Engineer", ext="r1")
    p2 = _posting("greenhouse", "Backend Engineer", ext="g1")
    results = [
        SourceResult(source="remotive", postings=[p1]),
        SourceResult(source="greenhouse", postings=[p2]),
    ]
    unique = dedupe_batch(results)
    assert len(unique) == 1
    assert unique[0].source == "remotive"


def test_dedupe_batch_keeps_distinct_locations():
    results = [
        SourceResult(
            source="a",
            postings=[
                _posting("a", "Backend Engineer", location="Berlin", ext="1"),
                _posting("a", "Backend Engineer", location="Munich", ext="2"),
            ],
        )
    ]
    assert len(dedupe_batch(results)) == 2
