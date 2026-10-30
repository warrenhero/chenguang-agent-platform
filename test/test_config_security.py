import pytest
from pydantic import ValidationError

from src.core.config import Settings


def _settings(**overrides) -> Settings:
    data = {
        "DB_PASSWORD": "test",
        "REDIS_PASSWORD": "test",
        "JWT_SECRET_KEY": "a" * 64,
    }
    data.update(overrides)
    return Settings(**data)


def test_accepts_valid_jwt_settings():
    settings = _settings()
    assert settings.JWT_ALGORITHM == "HS256"
    assert settings.JWT_EXPIRE_MINUTES == 30


def test_rejects_placeholder_secret():
    with pytest.raises(ValidationError, match="占位值"):
        _settings(JWT_SECRET_KEY="change-me-with-openssl-rand-hex-32")


def test_rejects_short_secret():
    with pytest.raises(ValidationError):
        _settings(JWT_SECRET_KEY="too-short")


def test_rejects_unsafe_algorithm():
    with pytest.raises(ValidationError, match="HS256"):
        _settings(JWT_ALGORITHM="none")


def test_rejects_non_positive_expire_minutes():
    with pytest.raises(ValidationError):
        _settings(JWT_EXPIRE_MINUTES=0)
