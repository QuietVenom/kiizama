import secrets
import warnings
from typing import Annotated, Any, Literal

from pydantic import (
    AnyUrl,
    BeforeValidator,
    EmailStr,
    HttpUrl,
    PostgresDsn,
    computed_field,
    model_validator,
)
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing_extensions import Self

INSECURE_PLACEHOLDER_VALUES = {"changethis", "ChangeThis1!"}


def parse_cors(v: Any) -> list[str] | str:
    if isinstance(v, str) and not v.startswith("["):
        return [i.strip() for i in v.split(",") if i.strip()]
    elif isinstance(v, list | str):
        return v
    raise ValueError(v)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        # Use top level .env file (one level above ./backend/)
        env_file="../.env",
        env_ignore_empty=True,
        extra="ignore",
    )
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = secrets.token_urlsafe(32)
    SECRET_KEY_IG_CREDENTIALS: str
    # 60 minutes * 24 hours * 8 days = 8 days
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8
    SYSTEM_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    # Canonical origin for backend-generated links to the authenticated app.
    FRONTEND_HOST: str = "http://localhost:5173"
    ENVIRONMENT: Literal["local", "staging", "production"] = "local"

    BACKEND_CORS_ORIGINS: Annotated[
        list[AnyUrl] | str, BeforeValidator(parse_cors)
    ] = []

    @computed_field  # type: ignore[prop-decorator]
    @property
    def all_cors_origins(self) -> list[str]:
        return [str(origin).rstrip("/") for origin in self.BACKEND_CORS_ORIGINS] + [
            self.FRONTEND_HOST
        ]

    PROJECT_NAME: str
    SENTRY_DSN: HttpUrl | None = None
    DATABASE_URL: str | None = None
    DATABASE_URL_PRODUCTION_INTERNAL: str | None = None
    POSTGRES_SERVER: str
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str = ""
    POSTGRES_DB: str = ""

    def _first_non_empty(self, *values: str | None) -> str | None:
        for value in values:
            if value and value.strip():
                return value.strip()
        return None

    def _normalize_postgres_url(self, raw_url: str) -> str:
        url = raw_url.strip()
        if url.startswith("postgres://"):
            url = f"postgresql://{url[len('postgres://') :]}"
        if url.startswith("postgresql://"):
            url = f"postgresql+psycopg://{url[len('postgresql://') :]}"
        return url

    def _resolved_database_url(self) -> str | None:
        if self.ENVIRONMENT == "production":
            candidate = self._first_non_empty(
                self.DATABASE_URL,
                self.DATABASE_URL_PRODUCTION_INTERNAL,
            )
        else:
            candidate = self._first_non_empty(self.DATABASE_URL)
        if not candidate:
            return None
        return self._normalize_postgres_url(candidate)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def SQLALCHEMY_DATABASE_URI(self) -> str:
        resolved_url = self._resolved_database_url()
        if resolved_url:
            return resolved_url
        return str(
            PostgresDsn.build(
                scheme="postgresql+psycopg",
                username=self.POSTGRES_USER,
                password=self.POSTGRES_PASSWORD,
                host=self.POSTGRES_SERVER,
                port=self.POSTGRES_PORT,
                path=self.POSTGRES_DB,
            )
        )

    RESEND_API_KEY: str | None = None
    EMAILS_FROM_EMAIL: EmailStr | None = None
    EMAILS_FROM_NAME: str | None = None

    @model_validator(mode="after")
    def _set_default_emails_from(self) -> Self:
        if not self.EMAILS_FROM_NAME:
            self.EMAILS_FROM_NAME = self.PROJECT_NAME
        return self

    EMAIL_RESET_TOKEN_EXPIRE_HOURS: int = 48

    @computed_field  # type: ignore[prop-decorator]
    @property
    def emails_enabled(self) -> bool:
        return bool(self.RESEND_API_KEY and self.EMAILS_FROM_EMAIL)

    EMAIL_TEST_USER: EmailStr = "test@example.com"
    FIRST_SUPERUSER: EmailStr
    FIRST_SUPERUSER_PASSWORD: str
    SYSTEM_ADMIN_EMAIL: EmailStr | None = None
    SYSTEM_ADMIN_PASSWORD: str | None = None

    REDIS_URL: str | None = None
    FLY_REDIS_URL: str | None = None
    RATE_LIMIT_ENABLED: bool = True
    JOB_CONTROL_TERMINAL_STATE_TTL_SECONDS: int = 60 * 60 * 24
    USER_EVENTS_STREAM_MAXLEN: int = 100
    USER_EVENTS_SSE_READ_BLOCK_MS: int = 10_000
    JOB_CONTROL_QUEUE_MAXLEN: int = 10_000

    def _resolved_redis_url(self) -> str | None:
        return self._first_non_empty(self.REDIS_URL, self.FLY_REDIS_URL)

    def _check_default_secret(self, var_name: str, value: str | None) -> None:
        if value in INSECURE_PLACEHOLDER_VALUES:
            message = (
                f"The value of {var_name} uses the insecure placeholder {value!r}, "
                "for security, please change it, at least for deployments."
            )
            if self.ENVIRONMENT == "local":
                warnings.warn(message, stacklevel=1)
            else:
                raise ValueError(message)

    @model_validator(mode="after")
    def _enforce_non_default_secrets(self) -> Self:
        self._check_default_secret("SECRET_KEY", self.SECRET_KEY)
        self._check_default_secret(
            "SECRET_KEY_IG_CREDENTIALS", self.SECRET_KEY_IG_CREDENTIALS
        )
        if not self._resolved_database_url():
            self._check_default_secret("POSTGRES_PASSWORD", self.POSTGRES_PASSWORD)
        self._check_default_secret(
            "FIRST_SUPERUSER_PASSWORD", self.FIRST_SUPERUSER_PASSWORD
        )
        if self.SYSTEM_ADMIN_PASSWORD:
            self._check_default_secret(
                "SYSTEM_ADMIN_PASSWORD", self.SYSTEM_ADMIN_PASSWORD
            )

        if self.ENVIRONMENT in {"staging", "production"} and (
            not self._resolved_redis_url()
        ):
            raise ValueError("REDIS_URL is required outside local environment.")
        if self.USER_EVENTS_SSE_READ_BLOCK_MS <= 0:
            raise ValueError("USER_EVENTS_SSE_READ_BLOCK_MS must be positive.")
        if self.USER_EVENTS_STREAM_MAXLEN <= 0:
            raise ValueError("USER_EVENTS_STREAM_MAXLEN must be positive.")
        if self.JOB_CONTROL_TERMINAL_STATE_TTL_SECONDS <= 0:
            raise ValueError("JOB_CONTROL_TERMINAL_STATE_TTL_SECONDS must be positive.")
        if self.JOB_CONTROL_QUEUE_MAXLEN <= 0:
            raise ValueError("JOB_CONTROL_QUEUE_MAXLEN must be positive.")

        return self


settings = Settings()  # type: ignore
