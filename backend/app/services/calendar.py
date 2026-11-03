"""
Calendar helpers used by the roadmap node: split the learning window into
weekday-only weeks, honouring blackout dates (holidays, exam week, etc.).
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import Iterable, List, Optional

from app.utils.helpers import parse_date


def week_windows(
    start: str | date,
    end:   str | date,
    blackout: Optional[Iterable[str]] = None,
) -> List[tuple[date, date]]:
    """
    Return a list of (monday, friday) tuples covering [start, end].
    Weeks that have *all* working days blacked-out are dropped entirely.
    """
    s = parse_date(start) if isinstance(start, str) else start
    e = parse_date(end)   if isinstance(end,   str) else end
    black = {parse_date(b) for b in (blackout or [])}

    # Anchor on the Monday of the start week
    monday = s - timedelta(days=s.weekday())

    out: List[tuple[date, date]] = []
    while monday <= e:
        working = [
            monday + timedelta(days=i)
            for i in range(5)
            if (monday + timedelta(days=i)) not in black
            and s <= (monday + timedelta(days=i)) <= e
        ]
        if working:
            out.append((working[0], working[-1]))
        monday += timedelta(days=7)

    return out
