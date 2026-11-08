"""Timestamp normalization shared by the fraud schema and rules.

Policy (documented in README):
* timezone-aware timestamps ("+01:00", "Z", ...) are CONVERTED to UTC - the offset is never just dropped;
* naive timestamps (no offset) are interpreted as UTC (the convention of the workflow and the synthetic data);
* anything that is not ISO-8601 is rejected with a ValueError (-> HTTP 422 / invalid_input).
"""
from __future__ import annotations

from datetime import datetime, timezone

TIMESTAMP_HELP = "ISO-8601 timestamp, e.g. 2026-11-08T10:00:00+01:00, 2026-11-08T09:00:00Z or 2026-11-08T09:00:00 (UTC)"


def parse_to_utc(ts: str | datetime) -> datetime:
    """Return an aware UTC datetime. Raises ValueError for unparseable input."""
    if isinstance(ts, datetime):
        dt = ts
    else:
        if not isinstance(ts, str) or not ts.strip():
            raise ValueError(f"empty timestamp; expected {TIMESTAMP_HELP}")
        try:
            dt = datetime.fromisoformat(ts.strip().replace("Z", "+00:00").replace("z", "+00:00"))
        except ValueError:
            raise ValueError(f"invalid timestamp {ts!r}; expected {TIMESTAMP_HELP}") from None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def to_utc_iso(ts: str | datetime) -> str:
    """Normalized string form: explicit UTC offset, e.g. '2026-11-08T09:00:00+00:00'."""
    return parse_to_utc(ts).isoformat()


def to_utc_naive(ts: str | datetime) -> datetime:
    """UTC wall-clock datetime without tzinfo, for safe comparisons between normalized timestamps."""
    return parse_to_utc(ts).replace(tzinfo=None)
