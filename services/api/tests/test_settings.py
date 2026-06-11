import os

import pytest

from app.settings import get_settings


def _set_base_env(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg2://user:pass@localhost:5432/soulmatch")
    monkeypatch.setenv("JWT_SECRET", "x" * 40)
    monkeypatch.setenv("PII_ENCRYPTION_KEY", "y" * 40)
    monkeypatch.setenv("APP_SUPPORT_EMAIL", "support@soulmatch.app")
    monkeypatch.setenv("APP_POLICY_BASE_URL", "https://soulmatch.app/legal")
    monkeypatch.setenv("APP_ACCOUNT_DELETE_URL", "https://soulmatch.app/account/delete")


def test_production_rejects_wildcard_cors(monkeypatch):
    _set_base_env(monkeypatch)
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("CORS_ALLOW_ORIGINS", "*")
    with pytest.raises(RuntimeError, match="Wildcard CORS"):
        get_settings()


def test_production_rejects_non_https_origin(monkeypatch):
    _set_base_env(monkeypatch)
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("CORS_ALLOW_ORIGINS", "http://app.soulmatch.app")
    with pytest.raises(RuntimeError, match="https"):
        get_settings()


def test_production_accepts_strict_cors(monkeypatch):
    _set_base_env(monkeypatch)
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("CORS_ALLOW_ORIGINS", "https://app.soulmatch.app,https://admin.soulmatch.app")
    settings = get_settings()
    assert settings.app_env == "production"
    assert settings.cors_allowed_origins == ["https://app.soulmatch.app", "https://admin.soulmatch.app"]


def test_production_rejects_short_jwt_secret(monkeypatch):
    _set_base_env(monkeypatch)
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("JWT_SECRET", "short")
    monkeypatch.setenv("CORS_ALLOW_ORIGINS", "https://app.soulmatch.app")
    with pytest.raises(RuntimeError, match="at least 32"):
        get_settings()


def test_development_allows_local_cors(monkeypatch):
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.delenv("CORS_ALLOW_ORIGINS", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("JWT_SECRET", raising=False)
    monkeypatch.delenv("PII_ENCRYPTION_KEY", raising=False)
    settings = get_settings()
    assert "http://localhost:8081" in settings.cors_allowed_origins
    assert settings.database_url.startswith("postgresql+psycopg2://")
