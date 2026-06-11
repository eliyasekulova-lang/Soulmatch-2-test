from datetime import datetime


def audit_metadata(duration_ms: float) -> dict:
    return {"duration_ms": round(duration_ms, 2), "recorded_at": datetime.utcnow().isoformat()}
