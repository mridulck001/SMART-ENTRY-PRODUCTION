"""
Time utility helpers for the Smart Entry System.
"""
from datetime import datetime, timezone


def utcnow() -> datetime:
    """Return current timezone-aware UTC datetime."""
    return datetime.now(timezone.utc)


def format_ist(dt: datetime) -> str:
    """
    Format a UTC datetime as IST (UTC+5:30) string.
    Example: '27 Feb 2026, 04:30 PM IST'
    """
    from datetime import timedelta
    if dt is None:
        return '—'
    ist_offset = timedelta(hours=5, minutes=30)
    ist_dt = dt.astimezone(timezone.utc) + ist_offset
    return ist_dt.strftime('%d %b %Y, %I:%M %p IST')


def format_iso(dt: datetime) -> str:
    """Return ISO 8601 string for a datetime, or empty string if None."""
    if dt is None:
        return ''
    return dt.isoformat()
