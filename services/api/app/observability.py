import json
import logging
import time
from datetime import datetime, timezone

from fastapi import FastAPI, Request
from sqlalchemy.exc import SQLAlchemyError

try:
    import sentry_sdk
except Exception:  # pragma: no cover - optional dependency in local bootstrap
    sentry_sdk = None

from .database import SessionLocal
from .models import AuditEvent
from .runtime_state import error_counters_snapshot, incr_error_counter
from .security import decode_token


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if hasattr(record, "request_id"):
            payload["request_id"] = getattr(record, "request_id")
        if hasattr(record, "method"):
            payload["method"] = getattr(record, "method")
        if hasattr(record, "path"):
            payload["path"] = getattr(record, "path")
        if hasattr(record, "status_code"):
            payload["status_code"] = getattr(record, "status_code")
        if hasattr(record, "duration_ms"):
            payload["duration_ms"] = getattr(record, "duration_ms")
        return json.dumps(payload, ensure_ascii=True)


def configure_logging(level: str = "INFO") -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())

    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.handlers = [handler]


def init_sentry(dsn: str, environment: str) -> None:
    if not dsn or sentry_sdk is None:
        return
    sentry_sdk.init(
        dsn=dsn,
        environment=environment,
        traces_sample_rate=0.1,
        profiles_sample_rate=0.0,
    )


def install_request_logging(app: FastAPI) -> None:
    logger = logging.getLogger("soulmatch.api")

    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        request_id = request.headers.get("x-request-id", f"req-{int(time.time() * 1000)}")
        started = time.perf_counter()
        response = await call_next(request)
        duration_ms = round((time.perf_counter() - started) * 1000, 2)
        logger.info(
            "request_completed",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": duration_ms,
            },
        )
        critical_prefixes = ("/auth", "/v1/auth", "/messages", "/v1/messages", "/matches", "/v1/matches", "/events", "/v1/events")
        if request.url.path.startswith(critical_prefixes):
            if response.status_code >= 500:
                incr_error_counter(f"{request.url.path}:5xx")
            elif response.status_code >= 400:
                incr_error_counter(f"{request.url.path}:4xx")
        response.headers["x-request-id"] = request_id
        return response


def install_audit_event_middleware(app: FastAPI) -> None:
    @app.middleware("http")
    async def audit_events(request: Request, call_next):
        started = time.perf_counter()
        response = await call_next(request)
        duration_ms = round((time.perf_counter() - started) * 1000, 2)

        actor_user_id = None
        auth_header = request.headers.get("authorization", "")
        if auth_header.lower().startswith("bearer "):
            token = auth_header.split(" ", 1)[1]
            payload = decode_token(token)
            if payload and payload.get("sub"):
                actor_user_id = payload["sub"]

        event = AuditEvent(
            actor_user_id=actor_user_id,
            actor_type="user" if actor_user_id else "system",
            event_type="http.request",
            path=request.url.path,
            method=request.method,
            status_code=response.status_code,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            metadata_json={"duration_ms": duration_ms},
            created_at=datetime.now(timezone.utc).replace(tzinfo=None),
        )
        try:
            with SessionLocal() as db:
                db.add(event)
                db.commit()
        except SQLAlchemyError:
            # Audit write should not break request path.
            pass
        return response


def get_error_metrics() -> dict[str, int]:
    return error_counters_snapshot()
