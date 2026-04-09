from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def parse_dt(val) -> datetime | None:
    if not val:
        return None
    if isinstance(val, datetime):
        return val if val.tzinfo else val.replace(tzinfo=timezone.utc)
    try:
        s = str(val).replace("Z", "+00:00")
        return datetime.fromisoformat(s)
    except Exception:
        return None


def session_minutes_by_calendar_day(start_utc: datetime, end_utc: datetime, tz: ZoneInfo) -> dict[str, float]:
    out: dict[str, float] = defaultdict(float)
    if end_utc <= start_utc:
        return dict(out)
    start_local = start_utc.astimezone(tz)
    end_local = end_utc.astimezone(tz)
    d = start_local.date()
    end_date = end_local.date()
    while d <= end_date:
        day_start = datetime(d.year, d.month, d.day, 0, 0, 0, tzinfo=tz)
        day_end = day_start + timedelta(days=1)
        seg_start = max(start_local, day_start)
        seg_end = min(end_local, day_end)
        if seg_end > seg_start:
            out[d.isoformat()] += (seg_end - seg_start).total_seconds() / 60.0
        d = d + timedelta(days=1)
    return dict(out)
