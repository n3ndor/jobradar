"""Environment loading. In GitHub Actions the env vars come from secrets;
locally they come from the repo-root .env.local (shared with Next.js)."""

from __future__ import annotations

import os
from pathlib import Path


def load_env() -> None:
    """Minimal .env loader: never overrides variables already set."""
    root = Path(__file__).resolve().parents[2]
    for name in (".env.local", ".env"):
        path = root / name
        if not path.is_file():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key, value = key.strip(), value.strip().strip("'\"")
            os.environ.setdefault(key, value)


def require(key: str) -> str:
    value = os.environ.get(key)
    if not value:
        raise SystemExit(f"Missing required environment variable: {key}")
    return value
