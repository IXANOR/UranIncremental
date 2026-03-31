"""Utilities for computing game-tick delta time.

Centralises the online/offline branching logic so it is tested independently
of the full game loop.
"""

from datetime import UTC, datetime


def ensure_utc(dt: datetime) -> datetime:
    """Return a timezone-aware datetime in UTC.

    SQLite stores datetimes without timezone info; this helper normalises them
    so subtraction is always valid.

    Args:
        dt: A datetime that may be timezone-naive (assumed UTC) or tz-aware.

    Returns:
        The same instant expressed as UTC-aware datetime.
    """
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def compute_delta(
    last_tick_at: datetime,
    now: datetime,
    offline_cap_seconds: int,
    offline_efficiency: float,
    *,
    is_offline: bool,
) -> tuple[float, bool]:
    """Compute how many effective seconds of production to simulate.

    Online ticks receive 100 % efficiency with no cap.
    Offline ticks are capped at ``offline_cap_seconds`` and scaled by
    ``offline_efficiency``.

    Args:
        last_tick_at: Timestamp of the previous tick.
        now: Current server timestamp.
        offline_cap_seconds: Maximum raw seconds that can be accumulated offline.
        offline_efficiency: Production multiplier when offline (e.g. 0.20).
        is_offline: Whether this tick is being treated as an offline period.

    Returns:
        Tuple of (effective_delta_seconds, cap_applied).
        ``effective_delta_seconds`` is already scaled by efficiency.
        ``cap_applied`` is True when the raw delta exceeded the cap.
    """
    raw_delta = max(0.0, (ensure_utc(now) - ensure_utc(last_tick_at)).total_seconds())

    if not is_offline:
        return raw_delta, False

    cap_applied = False
    if raw_delta > offline_cap_seconds:
        raw_delta = float(offline_cap_seconds)
        cap_applied = True

    return raw_delta * offline_efficiency, cap_applied
