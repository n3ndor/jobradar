import pytest

from pipeline import enrich_rules
from pipeline.tech_filter import is_tech_role


def classify(title="", location="", description=""):
    return enrich_rules.classify(
        {"title": title, "location_raw": location, "raw": {"description": description}}
    )


# --- seniority --------------------------------------------------------------

@pytest.mark.parametrize(
    "title,expected",
    [
        ("Principal Engineer", "principal"),
        ("Staff Software Engineer", "lead"),
        ("Engineering Lead", "lead"),
        ("Senior Backend Developer", "senior"),
        ("Junior Data Analyst", "junior"),
        ("Working Student Software", "junior"),
        ("Software Engineer", "mid"),
    ],
)
def test_seniority(title, expected):
    assert classify(title=title)["seniority"] == expected


def test_manager_is_not_forced_to_lead():
    # "manager" was intentionally removed from the lead bucket.
    assert classify(title="Product Manager")["seniority"] == "mid"


# --- stack detection & false positives --------------------------------------

def test_stack_detects_from_title_and_description():
    stack = classify(title="Backend Engineer", description="We use Python, Django and AWS.")["stack"]
    assert "Python" in stack and "Django" in stack and "AWS" in stack


def test_stack_avoids_substring_false_positives():
    # "scalable" must not match Scala; "specialists" must not match TS;
    # the English word "go" must not match Go.
    stack = classify(
        title="Data Specialists",
        description="Build scalable systems and go above expectations.",
    )["stack"]
    assert "Scala" not in stack
    assert "TypeScript" not in stack
    assert "Go" not in stack


def test_stack_detects_go_only_as_golang():
    assert "Go" in classify(title="Golang Engineer")["stack"]


# --- region -----------------------------------------------------------------

@pytest.mark.parametrize(
    "location,title,expected",
    [
        ("Berlin, Germany", "", "DACH"),
        ("San Francisco, CA", "", "US"),
        ("Remote, US", "", "US"),
        ("Toronto", "", "Canada"),
        ("London", "", "UK & Ireland"),
        ("", "Softwareentwickler (m/w/d)", "DACH"),  # German markers imply DACH
        ("Remote", "", "Global / Remote"),
        ("", "", "Unknown"),
    ],
)
def test_region(location, title, expected):
    assert classify(title=title, location=location)["region"] == expected


# --- remote policy ----------------------------------------------------------

@pytest.mark.parametrize(
    "location,expected",
    [
        ("Remote", "remote"),
        ("Hybrid - Berlin", "hybrid"),
        ("Berlin", "onsite"),
        ("", "unknown"),
    ],
)
def test_remote_policy(location, expected):
    assert classify(location=location)["remote_policy"] == expected


def test_dach_friendly():
    assert classify(location="Munich")["dach_friendly"] is True
    assert classify(location="Remote")["dach_friendly"] is True  # global remote
    assert classify(location="Remote, US")["dach_friendly"] is False
    assert classify(location="New York")["dach_friendly"] is False


def test_classify_marks_heuristic():
    result = classify(title="Software Engineer", location="Berlin")
    assert result["model"] == "rules"
    assert result["status"] == "heuristic"


# --- tech filter ------------------------------------------------------------

@pytest.mark.parametrize(
    "title",
    [
        "Senior Software Engineer",
        "Data Scientist",
        "DevOps Engineer",
        "Product Designer",
        "Softwareentwickler (m/w/d)",  # German
        "Ingenieur*in Systeme",
    ],
)
def test_is_tech_role_accepts(title):
    assert is_tech_role(title) is True


@pytest.mark.parametrize(
    "title",
    [
        "Account Executive",
        "Sales Assistant",
        "Office Manager",
        "Communications Manager",
    ],
)
def test_is_tech_role_rejects(title):
    assert is_tech_role(title) is False
