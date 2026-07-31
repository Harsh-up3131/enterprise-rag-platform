import pytest
from pydantic import ValidationError

from app.config import Settings


def test_production_requires_explicit_jwt_secret(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.delenv("JWT_SECRET", raising=False)
    monkeypatch.delenv("JWT_SECRET_FILE", raising=False)

    with pytest.raises(ValidationError):
        Settings()


def test_cors_allowed_origins_are_parsed_from_env(monkeypatch):
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", "https://a.example.com, https://b.example.com")

    settings = Settings()

    assert settings.cors_allowed_origins == ["https://a.example.com", "https://b.example.com"]
