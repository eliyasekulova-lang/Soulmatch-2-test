import os
from dataclasses import dataclass
from urllib.parse import urlparse


def _csv_to_list(raw: str) -> list[str]:
    return [item.strip() for item in raw.split(",") if item.strip()]


@dataclass(frozen=True)
class Settings:
    app_env: str
    app_name: str
    app_version: str
    database_url: str
    jwt_secret: str
    jwt_algorithm: str
    jwt_access_expire_minutes: int
    jwt_refresh_expire_days: int
    admin_emails: set[str]
    cors_allowed_origins: list[str]
    log_level: str
    sentry_dsn: str
    sentry_environment: str
    min_signup_age_years: int
    pii_encryption_key: str
    app_support_email: str
    app_policy_base_url: str
    app_account_delete_url: str
    auth_rate_limit_per_minute: int
    auth_refresh_rate_limit_per_minute: int
    message_send_rate_limit_per_minute: int
    stripe_secret_key: str
    stripe_webhook_secret: str
    stripe_premium_price_id: str
    resend_api_key: str
    anthropic_api_key: str


def get_settings() -> Settings:
    app_env = os.getenv("APP_ENV", "development").strip().lower()
    if app_env not in {"development", "staging", "production", "test"}:
        raise RuntimeError("APP_ENV must be one of: development, staging, production, test")

    default_dev_origins = [
        "http://localhost:19006",
        "http://127.0.0.1:19006",
        "http://localhost:8081",
        "http://127.0.0.1:8081",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

    raw_origins = os.getenv("CORS_ALLOW_ORIGINS", "")
    cors_allowed_origins = _csv_to_list(raw_origins) if raw_origins else default_dev_origins

    database_url = os.getenv("DATABASE_URL", "")
    if not database_url:
        if app_env in {"staging", "production"}:
            raise RuntimeError("DATABASE_URL is required in staging/production")
        database_url = "postgresql+psycopg2://postgres:postgres@localhost:5432/soulmatch"

    jwt_secret = os.getenv("JWT_SECRET", "dev-only-change-me")
    if app_env in {"staging", "production"}:
        if jwt_secret in {"", "dev-only-change-me", "change-me", "replace-with-a-long-random-secret"}:
            raise RuntimeError("JWT_SECRET must be explicitly set in staging/production")
        if len(jwt_secret) < 32:
            raise RuntimeError("JWT_SECRET must be at least 32 characters in staging/production")
    pii_encryption_key = os.getenv("PII_ENCRYPTION_KEY", "dev-only-pii-key-change-me")
    if app_env in {"staging", "production"} and pii_encryption_key in {
        "",
        "dev-only-pii-key-change-me",
        "replace-with-a-long-random-secret",
    }:
        raise RuntimeError("PII_ENCRYPTION_KEY must be explicitly set in staging/production")

    app_support_email = os.getenv("APP_SUPPORT_EMAIL", "").strip()
    app_policy_base_url = os.getenv("APP_POLICY_BASE_URL", "").strip()
    app_account_delete_url = os.getenv("APP_ACCOUNT_DELETE_URL", "").strip()
    if app_env in {"staging", "production"} and (not app_support_email or not app_policy_base_url or not app_account_delete_url):
        raise RuntimeError("APP_SUPPORT_EMAIL, APP_POLICY_BASE_URL, and APP_ACCOUNT_DELETE_URL are required in staging/production")

    if app_env in {"staging", "production"} and not cors_allowed_origins:
        raise RuntimeError("CORS_ALLOW_ORIGINS must be set in staging/production")

    if app_env in {"staging", "production"}:
        for origin in cors_allowed_origins:
            if origin == "*" or "*" in origin:
                raise RuntimeError("Wildcard CORS origins are forbidden in staging/production")
            parsed = urlparse(origin)
            if parsed.scheme != "https":
                raise RuntimeError(f"CORS origin must use https in staging/production: {origin}")
            if not parsed.netloc:
                raise RuntimeError(f"Invalid CORS origin: {origin}")
            if parsed.path not in {"", "/"}:
                raise RuntimeError(f"CORS origins must not include URL paths: {origin}")
            if parsed.hostname in {"localhost", "127.0.0.1"}:
                raise RuntimeError(f"localhost origins are forbidden in staging/production: {origin}")

    admin_emails = {email.strip().lower() for email in _csv_to_list(os.getenv("ADMIN_EMAILS", ""))}

    return Settings(
        app_env=app_env,
        app_name="SoulMatch API",
        app_version="0.5.0",
        database_url=database_url,
        jwt_secret=jwt_secret,
        jwt_algorithm=os.getenv("JWT_ALGORITHM", "HS256"),
        jwt_access_expire_minutes=int(os.getenv("JWT_ACCESS_EXPIRE_MINUTES", "30")),
        jwt_refresh_expire_days=int(os.getenv("JWT_REFRESH_EXPIRE_DAYS", "30")),
        admin_emails=admin_emails,
        cors_allowed_origins=cors_allowed_origins,
        log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
        sentry_dsn=os.getenv("SENTRY_DSN", "").strip(),
        sentry_environment=os.getenv("SENTRY_ENVIRONMENT", app_env),
        min_signup_age_years=int(os.getenv("MIN_SIGNUP_AGE_YEARS", "18")),
        pii_encryption_key=pii_encryption_key,
        app_support_email=app_support_email or "support@soulmatch.app",
        app_policy_base_url=app_policy_base_url or "https://soulmatch.app/legal",
        app_account_delete_url=app_account_delete_url or "https://soulmatch.app/account/delete",
        auth_rate_limit_per_minute=int(os.getenv("AUTH_RATE_LIMIT_PER_MINUTE", "25")),
        auth_refresh_rate_limit_per_minute=int(os.getenv("AUTH_REFRESH_RATE_LIMIT_PER_MINUTE", "15")),
        message_send_rate_limit_per_minute=int(os.getenv("MESSAGE_SEND_RATE_LIMIT_PER_MINUTE", "30")),
        stripe_secret_key=os.getenv("STRIPE_SECRET_KEY", "").strip(),
        stripe_webhook_secret=os.getenv("STRIPE_WEBHOOK_SECRET", "").strip(),
        stripe_premium_price_id=os.getenv("STRIPE_PREMIUM_PRICE_ID", "").strip(),
        resend_api_key=os.getenv("RESEND_API_KEY", "").strip(),
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY", "").strip(),
    )
