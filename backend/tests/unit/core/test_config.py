import warnings
from typing import Any

import pytest
from pydantic import ValidationError

from app.core.config import Settings, parse_cors


def _settings_kwargs(**overrides: Any) -> dict[str, Any]:
    values: dict[str, Any] = {
        "PROJECT_NAME": "Kiizama Test",
        "SECRET_KEY": "safe-secret-key",
        "SECRET_KEY_IG_CREDENTIALS": "safe-ig-secret-key",
        "FIRST_SUPERUSER": "admin@example.com",
        "FIRST_SUPERUSER_PASSWORD": "SafePass1!",
        "POSTGRES_SERVER": "localhost",
        "POSTGRES_USER": "postgres",
        "POSTGRES_PASSWORD": "safe-postgres-password",
        "POSTGRES_DB": "app",
        "REDIS_URL": "redis://localhost:6379/0",
    }
    values.update(overrides)
    return values


def test_parse_cors_csv_string_returns_trimmed_origins() -> None:
    result = parse_cors("https://one.test, https://two.test,,")

    assert result == ["https://one.test", "https://two.test"]


def test_settings_cors_origins_strip_trailing_slashes_and_add_frontend() -> None:
    settings = Settings(
        **_settings_kwargs(
            BACKEND_CORS_ORIGINS=["https://api.example.com/"],
            FRONTEND_HOST="https://app.example.com",
        )
    )

    assert settings.all_cors_origins == [
        "https://api.example.com",
        "https://app.example.com",
    ]


def test_settings_normalizes_postgres_urls_to_psycopg_scheme() -> None:
    settings = Settings(
        **_settings_kwargs(DATABASE_URL="postgres://user:pass@db.example.com/app")
    )

    assert settings.SQLALCHEMY_DATABASE_URI == (
        "postgresql+psycopg://user:pass@db.example.com/app"
    )


def test_settings_database_url_does_not_require_legacy_split_postgres_values() -> None:
    settings_kwargs = _settings_kwargs(
        ENVIRONMENT="production",
        DATABASE_URL="postgres://user:pass@db.example.com/app",
        POSTGRES_SERVER="",
        POSTGRES_USER="",
    )

    settings = Settings(**settings_kwargs)

    assert settings.SQLALCHEMY_DATABASE_URI == (
        "postgresql+psycopg://user:pass@db.example.com/app"
    )


def test_settings_staging_requires_redis_url() -> None:
    with pytest.raises(ValidationError, match="REDIS_URL is required"):
        Settings(
            **_settings_kwargs(
                ENVIRONMENT="staging",
                REDIS_URL=None,
                FLY_REDIS_URL=None,
            )
        )


def test_settings_user_events_defaults_match_transient_stream_policy() -> None:
    settings = Settings(**_settings_kwargs())

    assert settings.USER_EVENTS_STREAM_MAXLEN == 25
    assert settings.USER_EVENTS_STREAM_TTL_SECONDS == 60 * 60 * 24 * 7


def test_settings_user_events_stream_ttl_must_be_positive() -> None:
    with pytest.raises(
        ValidationError,
        match="USER_EVENTS_STREAM_TTL_SECONDS must be positive",
    ):
        Settings(**_settings_kwargs(USER_EVENTS_STREAM_TTL_SECONDS=0))


def test_settings_local_placeholder_secret_warns_instead_of_raising() -> None:
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        Settings(**_settings_kwargs(ENVIRONMENT="local", SECRET_KEY="changethis"))

    assert any("insecure placeholder" in str(warning.message) for warning in caught)


def test_settings_non_local_placeholder_secret_raises_validation_error() -> None:
    with pytest.raises(ValidationError, match="insecure placeholder"):
        Settings(**_settings_kwargs(ENVIRONMENT="production", SECRET_KEY="changethis"))


def test_parse_cors_rejects_unsupported_value() -> None:
    with pytest.raises(ValueError):
        parse_cors({"origin": "https://example.com"})
