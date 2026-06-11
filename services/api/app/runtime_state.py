from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone

_started_at = datetime.now(timezone.utc).replace(tzinfo=None)
_startup_ok = False
_startup_error: str | None = None
_last_startup_checked_at = _started_at
_error_counters: dict[str, int] = defaultdict(int)


def mark_startup_ok() -> None:
    global _startup_ok, _startup_error, _last_startup_checked_at
    _startup_ok = True
    _startup_error = None
    _last_startup_checked_at = datetime.now(timezone.utc).replace(tzinfo=None)


def mark_startup_error(error: str) -> None:
    global _startup_ok, _startup_error, _last_startup_checked_at
    _startup_ok = False
    _startup_error = error[:500]
    _last_startup_checked_at = datetime.now(timezone.utc).replace(tzinfo=None)


def startup_snapshot() -> dict:
    return {
        "started_at": _started_at.isoformat(),
        "startup_ok": _startup_ok,
        "startup_error": _startup_error,
        "last_startup_checked_at": _last_startup_checked_at.isoformat(),
    }


def incr_error_counter(key: str) -> None:
    _error_counters[key] += 1


def error_counters_snapshot() -> dict[str, int]:
    return dict(_error_counters)
