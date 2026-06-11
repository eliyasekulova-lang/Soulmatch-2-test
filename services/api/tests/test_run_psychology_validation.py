from scripts.run_psychology_validation import _database_kind, _resolve_database_url, _run_alembic_smoke


def test_resolve_database_url_prefers_explicit_argument(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg2://env-user:env-pass@db.example.com:5432/soulmatch")

    db_url, source = _resolve_database_url("postgresql+psycopg2://arg-user:arg-pass@db.example.com:5432/soulmatch")

    assert source == "explicit"
    assert db_url == "postgresql+psycopg2://arg-user:arg-pass@db.example.com:5432/soulmatch"


def test_resolve_database_url_falls_back_to_environment(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg2://env-user:env-pass@db.example.com:5432/soulmatch")

    db_url, source = _resolve_database_url(None)

    assert source == "environment"
    assert db_url == "postgresql+psycopg2://env-user:env-pass@db.example.com:5432/soulmatch"


def test_resolve_database_url_uses_temporary_sqlite_when_missing(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)

    db_url, source = _resolve_database_url(None)

    assert source == "temporary_sqlite"
    assert db_url is None


def test_database_kind_classifies_supported_backends():
    assert _database_kind("postgresql+psycopg2://user:pass@db.example.com:5432/soulmatch") == "postgres"
    assert _database_kind("sqlite:////tmp/soulmatch.db") == "sqlite"
    assert _database_kind("mysql://user:pass@db.example.com/soulmatch") == "other"


def test_run_alembic_smoke_skips_for_sqlite():
    result = _run_alembic_smoke("/tmp/fake-python", "sqlite:////tmp/soulmatch.db")

    assert result.status == "skip"
    assert "PostgreSQL DATABASE_URL" in result.detail
