from pipeline.enrichment import llm_update_row
from pipeline.providers import LlmResult


def _posting(**overrides):
    base = {
        "posting_id": 1,
        "title": "Engineer",
        "company": "Acme",
        "location_raw": "Remote",
        "raw": {},
        "remote_policy": "remote",
        "region": "Global / Remote",
        "dach_friendly": True,
    }
    base.update(overrides)
    return base


def test_llm_overrides_wrong_remote_tag():
    # The classic bug: board flags it remote, description says onsite Munich.
    result = LlmResult(summary="Role in Munich", remote_policy="onsite", region="DACH")
    row = llm_update_row(_posting(), result, "m", 10)
    assert row["remote_policy"] == "onsite"
    assert row["region"] == "DACH"
    assert row["dach_friendly"] is True  # Munich is DACH, onsite but local


def test_llm_demotes_fake_global_remote_to_us():
    result = LlmResult(summary="US-only remote", remote_policy="remote", region="US")
    row = llm_update_row(_posting(), result, "m", 10)
    assert row["region"] == "US"
    assert row["dach_friendly"] is False  # remote but US-locked


def test_llm_abstains_keeps_heuristic_values():
    result = LlmResult(summary="Vague posting", remote_policy="unknown", region=None)
    row = llm_update_row(_posting(), result, "m", 10)
    assert row["remote_policy"] == "remote"  # heuristic kept
    assert row["region"] == "Global / Remote"
    assert row["dach_friendly"] is True


def test_llm_invalid_region_value_ignored():
    result = LlmResult(summary="x", remote_policy="onsite", region="Mars")
    row = llm_update_row(_posting(), result, "m", 10)
    assert row["region"] == "Global / Remote"  # invalid value ignored, heuristic kept


def test_row_always_has_uniform_keys():
    # Bulk upsert requires every row to carry the same columns.
    a = llm_update_row(_posting(), LlmResult(summary="a"), "m", 1)
    b = llm_update_row(
        _posting(), LlmResult(summary="b", remote_policy="hybrid", region="Europe"), "m", 2
    )
    assert set(a.keys()) == set(b.keys())


def test_genuine_global_remote_stays_dach_friendly():
    result = LlmResult(
        summary="Work from anywhere", remote_policy="remote", region="Global / Remote"
    )
    row = llm_update_row(_posting(dach_friendly=False), result, "m", 10)
    assert row["dach_friendly"] is True
