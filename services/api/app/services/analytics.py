"""Lightweight PostHog analytics client for server-side event tracking."""
from __future__ import annotations

import logging

import httpx

logger = logging.getLogger("soulmatch.analytics")

_POSTHOG_HOST = "https://app.posthog.com"


def track(event: str, distinct_id: str, properties: dict | None = None, *, api_key: str) -> None:
    """Fire a PostHog event in a best-effort, non-blocking way.

    Always call with `.catch`-style error handling — never raise to the caller.
    """
    if not api_key or not distinct_id:
        return
    payload = {
        "api_key": api_key,
        "event": event,
        "distinct_id": distinct_id,
        "properties": properties or {},
    }
    try:
        with httpx.Client(timeout=3.0) as client:
            client.post(f"{_POSTHOG_HOST}/capture/", json=payload)
    except Exception as exc:
        logger.debug("posthog_capture_failed", extra={"event": event, "error": str(exc)})
