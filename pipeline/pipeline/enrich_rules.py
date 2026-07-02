"""Deterministic enrichment: derive structured fields from a posting with rules,
no LLM. Fast, free, unlimited. The Gemini layer later upgrades these rows with a
prose summary and parsed salary; until then, this alone powers the dashboard filters.
"""

from __future__ import annotations

import re

# --- tech stack -------------------------------------------------------------
# Canonical name -> regex of aliases. Word-boundary matched against title + description.
STACK: dict[str, str] = {
    "Python": r"python",
    "JavaScript": r"javascript|\bjs\b",
    "TypeScript": r"typescript|\bts\b",
    "React": r"\breact(?:\.?js)?\b|reactjs",
    "Next.js": r"next\.?js",
    "Vue": r"\bvue(?:\.?js)?\b",
    "Angular": r"angular",
    "Node.js": r"node\.?js|nodejs",
    "Go": r"\bgolang\b",
    "Rust": r"\brust\b",
    "Java": r"\bjava\b",
    "Kotlin": r"kotlin",
    "Swift": r"\bswift\b",
    "C++": r"c\+\+",
    "C#": r"c#|\.net|dotnet",
    "Ruby": r"ruby(?:\s*on\s*rails)?|rails",
    "PHP": r"\bphp\b",
    "Scala": r"\bscala\b",
    "Elixir": r"elixir",
    "SQL": r"\bsql\b|postgres|postgresql|mysql",
    "GraphQL": r"graphql",
    "AWS": r"\baws\b|amazon web services",
    "GCP": r"\bgcp\b|google cloud",
    "Azure": r"azure",
    "Kubernetes": r"kubernetes|k8s",
    "Docker": r"docker",
    "Terraform": r"terraform",
    "SAP": r"\bsap\b",
    "Salesforce": r"salesforce",
    "Django": r"django",
    "Flask": r"flask",
    "Spring": r"spring boot|spring framework",
    "TensorFlow": r"tensorflow",
    "PyTorch": r"pytorch",
    "Spark": r"apache spark|\bspark\b",
    "Kafka": r"kafka",
    "Redis": r"redis",
    "MongoDB": r"mongodb|mongo\b",
}
_STACK_COMPILED = {name: re.compile(rx, re.IGNORECASE) for name, rx in STACK.items()}

# --- seniority (most senior first wins) -------------------------------------
_SENIORITY = [
    ("principal", r"principal|distinguished|\bfellow\b"),
    ("lead", r"\blead\b|\bhead\b|\bstaff\b|director|\bvp\b"),
    ("senior", r"senior|\bsr\.?\b|expert|iii\b"),
    ("junior", r"junior|\bjr\.?\b|intern|working student|werkstudent|graduate|entry[- ]level"),
]
_SENIORITY_COMPILED = [(lvl, re.compile(rx, re.IGNORECASE)) for lvl, rx in _SENIORITY]

# --- region buckets ---------------------------------------------------------
_REGION = [
    ("DACH", r"german|deutschland|\bberlin\b|munich|münchen|hamburg|frankfurt|cologne|köln|"
             r"stuttgart|düsseldorf|dusseldorf|leipzig|dresden|hannover|nürnberg|nuremberg|"
             r"bonn|essen|dortmund|bremen|tübingen|tubingen|freiburg|mannheim|karlsruhe|"
             r"bayern|bavaria|sachsen|brandenburg|"
             r"austria|österreich|vienna|wien|switzerland|schweiz|zurich|zürich|\bdach\b"),
    ("UK & Ireland", r"united kingdom|\buk\b|england|london|scotland|ireland|dublin"),
    ("Europe", r"\beurope\b|\bemea\b|\beu\b|france|paris|spain|madrid|barcelona|italy|"
               r"netherlands|amsterdam|poland|sweden|portugal|lisbon"),
    ("US", r"united states|\bus\b|\busa\b|\bu\.s\.|new york|san francisco|remote, us|"
           r"california|texas|seattle|boston|chicago|\bny\b|\bca\b"),
    ("Canada", r"canada|toronto|vancouver|montreal"),
    ("APAC", r"\bapac\b|singapore|india|bangalore|tokyo|japan|australia|sydney|china"),
    ("LATAM", r"\blatam\b|brazil|mexico|argentina|colombia"),
]
_REGION_COMPILED = [(name, re.compile(rx, re.IGNORECASE)) for name, rx in _REGION]

_DACH_RE = _REGION_COMPILED[0][1]
_REMOTE_RE = re.compile(r"remote|anywhere|distributed|work from home|home office", re.IGNORECASE)
_HYBRID_RE = re.compile(r"hybrid", re.IGNORECASE)

# German job-posting conventions: a strong DACH signal even without a city name.
_GERMAN_RE = re.compile(
    r"m/w/d|w/m/d|m/f/d|\(m/w\)|gmbh\b|\bag\b|ausbildung|praktikum|werkstudent|"
    r"teilzeit|vollzeit|mitarbeiter|standort|berater",
    re.IGNORECASE,
)


def _haystack(posting: dict) -> str:
    raw = posting.get("raw") or {}
    return " ".join(
        str(x) for x in (posting.get("title", ""), (raw.get("description") or "")[:4000])
    )


def detect_stack(posting: dict) -> list[str]:
    text = _haystack(posting)
    return sorted(name for name, rx in _STACK_COMPILED.items() if rx.search(text))


def detect_seniority(title: str) -> str:
    for level, rx in _SENIORITY_COMPILED:
        if rx.search(title):
            return level
    return "mid"


def detect_region(location: str, title: str = "") -> str:
    for name, rx in _REGION_COMPILED:
        if rx.search(location):
            return name
    # German-language markers in the title imply a DACH posting (common on Arbeitnow).
    if _GERMAN_RE.search(f"{location} {title}"):
        return "DACH"
    if not location.strip():
        return "Unknown"
    if _REMOTE_RE.search(location):
        return "Global / Remote"
    return "Other"


def detect_remote_policy(location: str, title: str) -> str:
    blob = f"{location} {title}"
    if _HYBRID_RE.search(blob):
        return "hybrid"
    if _REMOTE_RE.search(blob):
        return "remote"
    if location.strip():
        return "onsite"
    return "unknown"


def is_dach_friendly(location: str, title: str, remote_policy: str) -> bool:
    if _DACH_RE.search(location) or _GERMAN_RE.search(f"{location} {title}"):
        return True
    # A globally-remote role with no country restriction is reachable from the DACH region.
    return remote_policy == "remote" and not re.search(
        r"remote,\s*(us|usa|canada|india)", location, re.IGNORECASE
    )


def classify(posting: dict) -> dict:
    """Return an enrichments row (minus posting_id) derived purely from rules."""
    title = posting.get("title", "")
    location = posting.get("location_raw", "")
    remote_policy = detect_remote_policy(location, title)
    return {
        "seniority": detect_seniority(title),
        "stack": detect_stack(posting),
        "remote_policy": remote_policy,
        "region": detect_region(location, title),
        "dach_friendly": is_dach_friendly(location, title, remote_policy),
        "model": "rules",
        "status": "heuristic",
    }
