"""JobRadar tracks tech roles only (engineering, data, design, product).

This is the single definition of "tech role", applied to every source in the
pipeline so the product's 'tech only' claim stays true no matter which adapter
a posting came from.
"""

from __future__ import annotations

import re

TECH_TITLE = re.compile(
    r"\b("
    r"engineer(?:ing)?|ingenieur|informatiker?|developer|entwickler|software|programmer|programmierer|sre|devops|"
    r"data\s*(scientist|engineer|analyst)|machine\s*learning|ml\b|ai\b|"
    r"backend|back-end|frontend|front-end|full\s*stack|fullstack|"
    r"infrastructure|platform|security|cloud|mobile|ios|android|"
    r"informatik|systemadministrator|system\s*administrator|sysadmin|it[- ](specialist|support|consultant|berater|administrator)|"
    r"designer|ux\b|ui\b|product\s*(manager|owner)|architect|architekt|qa\b|test(?:er|ing)?\b|"
    r"analytics|scientist|research|crypto|blockchain|sap\b|salesforce|erp\b|"
    r"webmaster|web\s*(developer|designer)|database|datenbank"
    r")",
    re.IGNORECASE,
)


def is_tech_role(title: str) -> bool:
    return bool(TECH_TITLE.search(title))
