"""
Shared, provider-agnostic utilities.

Most nodes already import extract_json from app.utils.parser. This file adds
a few small helpers that were being reinvented across routers.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Iterable, List, Optional
import re


GITHUB_RE = re.compile(
    r"^https?://github\.com/(?P<owner>[A-Za-z0-9_.-]+)/(?P<repo>[A-Za-z0-9_.-]+?)(?:\.git)?/?$"
)


def parse_github_url(url: str) -> Optional[tuple[str, str]]:
    """Return (owner, repo) or None if the URL isn't a valid GitHub repo URL."""
    if not url:
        return None
    m = GITHUB_RE.match(url.strip())
    if not m:
        return None
    return m.group("owner"), m.group("repo")


def parse_date(s: str) -> date:
    """Parse YYYY-MM-DD → date. Raise ValueError on failure."""
    return datetime.strptime(s, "%Y-%m-%d").date()


def working_days(
    start: str | date,
    end: str | date,
    blackout: Optional[Iterable[str]] = None,
) -> List[date]:
    """Return weekday-only dates in [start, end], minus any blackout dates."""
    s = parse_date(start) if isinstance(start, str) else start
    e = parse_date(end)   if isinstance(end,   str) else end
    black = {parse_date(b) for b in (blackout or [])}

    out: List[date] = []
    d = s
    while d <= e:
        if d.weekday() < 5 and d not in black:
            out.append(d)
        d += timedelta(days=1)
    return out


def weeks_between(start: str | date, end: str | date) -> int:
    """Inclusive, rounded-up number of calendar weeks between two dates."""
    s = parse_date(start) if isinstance(start, str) else start
    e = parse_date(end)   if isinstance(end,   str) else end
    days = max(0, (e - s).days) + 1
    return max(1, -(-days // 7))


def clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def score_to_display(score: float) -> float:
    """Map evaluator's -5..+5 range onto a friendlier 0..10 display score."""
    return round(clamp((score + 5.0), 0.0, 10.0), 1)
