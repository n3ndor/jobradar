from datetime import datetime, timezone

from pipeline.models import RawPosting, RunMetrics, posting_hash, posting_row


def test_hash_is_stable_and_normalized():
    # Same posting with different whitespace/case produces the same hash.
    a = posting_hash("Acme  Inc", "Senior  Engineer", "Berlin")
    b = posting_hash("acme inc", "senior engineer", "BERLIN")
    assert a == b
    assert len(a) == 64  # sha256 hex


def test_hash_distinguishes_different_postings():
    assert posting_hash("Acme", "Engineer", "Berlin") != posting_hash(
        "Acme", "Engineer", "Munich"
    )


def test_rawposting_hash_and_row():
    p = RawPosting(
        source="remotive",
        external_id="42",
        company="Acme",
        title="Backend Engineer",
        url="https://example.com/jobs/42",
        location_raw="Remote",
    )
    row = posting_row(p, source_id=7)
    assert row["source_id"] == 7
    assert row["hash"] == p.hash
    assert row["url"] == "https://example.com/jobs/42"
    assert row["posted_at"] is None


def test_runmetrics_duration_and_row():
    m = RunMetrics(
        started_at=datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
        finished_at=datetime(2026, 1, 1, 12, 0, 30, tzinfo=timezone.utc),
        fetched=10,
        new_postings=3,
    )
    assert m.duration_s == 30.0
    row = m.to_row()
    assert row["fetched"] == 10
    assert row["new_postings"] == 3
    assert row["duration_s"] == 30.0
