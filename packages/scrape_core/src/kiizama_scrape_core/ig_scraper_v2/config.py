from __future__ import annotations

import os
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field

from .constants import DEFAULT_USER_AGENT

DEFAULT_HEADLESS = True
DEFAULT_LOCALE = "en-US"
DEFAULT_MAX_CONCURRENT = 2
DEFAULT_MAX_POSTS = 12
DEFAULT_TIMEOUT_MS = 30_000
DEFAULT_VIEWPORT_HEIGHT = 1080
DEFAULT_VIEWPORT_WIDTH = 1920
DEFAULT_MAX_REQUEST_RETRIES = 3
DEFAULT_USE_SESSION_POOL = True
DEFAULT_PACING_ENABLED = True
DEFAULT_PACING_MIN_SECONDS = 1.0
DEFAULT_PACING_MAX_SECONDS = 3.0
DEFAULT_LOCAL_WARMUP_MIN_SECONDS = 1.5
DEFAULT_LOCAL_WARMUP_MAX_SECONDS = 4.0
DEFAULT_ISP_PROXY_WARMUP_MIN_SECONDS = 8.0
DEFAULT_ISP_PROXY_WARMUP_MAX_SECONDS = 20.0

ENVIRONMENT_ENV_VAR = "ENVIRONMENT"
USE_ISP_PROXY_ENV_VAR = "IG_SCRAPER_V2_USE_ISP_PROXY"
ISP_PROXY_URLS_ENV_VAR = "IG_SCRAPER_V2_ISP_PROXY_URLS"
MAX_CONCURRENT_ENV_VAR = "IG_SCRAPER_V2_MAX_CONCURRENT"
MAX_POSTS_ENV_VAR = "IG_SCRAPER_V2_MAX_POSTS"
HEADLESS_ENV_VAR = "IG_SCRAPER_V2_HEADLESS"
TIMEOUT_MS_ENV_VAR = "IG_SCRAPER_V2_TIMEOUT_MS"
LOCALE_ENV_VAR = "IG_SCRAPER_V2_LOCALE"
PACING_ENABLED_ENV_VAR = "IG_SCRAPER_V2_PACING_ENABLED"
PACING_MIN_SECONDS_ENV_VAR = "IG_SCRAPER_V2_PACING_MIN_SECONDS"
PACING_MAX_SECONDS_ENV_VAR = "IG_SCRAPER_V2_PACING_MAX_SECONDS"
WARMUP_MIN_SECONDS_ENV_VAR = "IG_SCRAPER_V2_WARMUP_MIN_SECONDS"
WARMUP_MAX_SECONDS_ENV_VAR = "IG_SCRAPER_V2_WARMUP_MAX_SECONDS"


@dataclass(frozen=True, slots=True)
class BrowserConfig:
    headless: bool = DEFAULT_HEADLESS
    timeout_ms: int = DEFAULT_TIMEOUT_MS
    user_agent: str = DEFAULT_USER_AGENT
    locale: str = DEFAULT_LOCALE
    viewport_width: int = DEFAULT_VIEWPORT_WIDTH
    viewport_height: int = DEFAULT_VIEWPORT_HEIGHT

    def __post_init__(self) -> None:
        _ensure_positive_int("timeout_ms", self.timeout_ms)
        _ensure_non_empty_string("user_agent", self.user_agent)
        _ensure_non_empty_string("locale", self.locale)
        _ensure_positive_int("viewport_width", self.viewport_width)
        _ensure_positive_int("viewport_height", self.viewport_height)


@dataclass(frozen=True, slots=True)
class CrawlerConfig:
    max_concurrent: int = DEFAULT_MAX_CONCURRENT
    max_request_retries: int = DEFAULT_MAX_REQUEST_RETRIES
    use_session_pool: bool = DEFAULT_USE_SESSION_POOL

    def __post_init__(self) -> None:
        _ensure_positive_int("max_concurrent", self.max_concurrent)
        if self.max_request_retries < 0:
            raise ValueError("max_request_retries must be zero or greater.")


@dataclass(frozen=True, slots=True)
class ProxyConfig:
    use_isp_proxy: bool = False
    proxy_urls: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        proxy_urls = _normalize_proxy_urls(self.proxy_urls)
        object.__setattr__(self, "proxy_urls", proxy_urls)
        if self.use_isp_proxy and not proxy_urls:
            raise ValueError(
                "At least one proxy URL is required when ISP proxy mode is enabled."
            )


@dataclass(frozen=True, slots=True)
class PacingConfig:
    enabled: bool = DEFAULT_PACING_ENABLED
    min_delay_seconds: float = DEFAULT_PACING_MIN_SECONDS
    max_delay_seconds: float = DEFAULT_PACING_MAX_SECONDS
    warmup_min_seconds: float = DEFAULT_LOCAL_WARMUP_MIN_SECONDS
    warmup_max_seconds: float = DEFAULT_LOCAL_WARMUP_MAX_SECONDS

    def __post_init__(self) -> None:
        _ensure_non_negative_float("min_delay_seconds", self.min_delay_seconds)
        _ensure_non_negative_float("max_delay_seconds", self.max_delay_seconds)
        _ensure_non_negative_float("warmup_min_seconds", self.warmup_min_seconds)
        _ensure_non_negative_float("warmup_max_seconds", self.warmup_max_seconds)
        if self.min_delay_seconds > self.max_delay_seconds:
            raise ValueError(
                "min_delay_seconds must be lower than or equal to max_delay_seconds."
            )
        if self.warmup_min_seconds > self.warmup_max_seconds:
            raise ValueError(
                "warmup_min_seconds must be lower than or equal to warmup_max_seconds."
            )


@dataclass(frozen=True, slots=True)
class ScraperV2Config:
    browser: BrowserConfig = field(default_factory=BrowserConfig)
    crawler: CrawlerConfig = field(default_factory=CrawlerConfig)
    proxy: ProxyConfig = field(default_factory=ProxyConfig)
    pacing: PacingConfig = field(default_factory=PacingConfig)
    max_posts: int = DEFAULT_MAX_POSTS

    def __post_init__(self) -> None:
        _ensure_positive_int("max_posts", self.max_posts)


def build_scraper_v2_config(
    *,
    env: Mapping[str, str] | None = None,
    headless: bool | None = None,
    timeout_ms: int | None = None,
    user_agent: str | None = None,
    locale: str | None = None,
    viewport_width: int | None = None,
    viewport_height: int | None = None,
    max_concurrent: int | None = None,
    max_posts: int | None = None,
    max_request_retries: int | None = None,
    use_session_pool: bool | None = None,
    use_isp_proxy: bool | None = None,
    proxy_urls: Iterable[str] | str | None = None,
    pacing_enabled: bool | None = None,
    pacing_min_seconds: float | None = None,
    pacing_max_seconds: float | None = None,
    warmup_min_seconds: float | None = None,
    warmup_max_seconds: float | None = None,
) -> ScraperV2Config:
    source = os.environ if env is None else env
    force_isp_proxy = _is_production_environment(source)
    resolved_use_isp_proxy = (
        True
        if force_isp_proxy
        else _coalesce(
            use_isp_proxy,
            _read_bool(source, USE_ISP_PROXY_ENV_VAR, False),
        )
    )
    default_warmup_min_seconds = (
        DEFAULT_ISP_PROXY_WARMUP_MIN_SECONDS
        if resolved_use_isp_proxy
        else DEFAULT_LOCAL_WARMUP_MIN_SECONDS
    )
    default_warmup_max_seconds = (
        DEFAULT_ISP_PROXY_WARMUP_MAX_SECONDS
        if resolved_use_isp_proxy
        else DEFAULT_LOCAL_WARMUP_MAX_SECONDS
    )

    browser = BrowserConfig(
        headless=_coalesce(
            headless,
            _read_bool(source, HEADLESS_ENV_VAR, DEFAULT_HEADLESS),
        ),
        timeout_ms=_coalesce(
            timeout_ms,
            _read_int(source, TIMEOUT_MS_ENV_VAR, DEFAULT_TIMEOUT_MS),
        ),
        user_agent=user_agent or DEFAULT_USER_AGENT,
        locale=_coalesce(locale, _read_string(source, LOCALE_ENV_VAR, DEFAULT_LOCALE)),
        viewport_width=viewport_width or DEFAULT_VIEWPORT_WIDTH,
        viewport_height=viewport_height or DEFAULT_VIEWPORT_HEIGHT,
    )
    crawler = CrawlerConfig(
        max_concurrent=_coalesce(
            max_concurrent,
            _read_int(source, MAX_CONCURRENT_ENV_VAR, DEFAULT_MAX_CONCURRENT),
        ),
        max_request_retries=_coalesce(
            max_request_retries,
            DEFAULT_MAX_REQUEST_RETRIES,
        ),
        use_session_pool=_coalesce(use_session_pool, DEFAULT_USE_SESSION_POOL),
    )
    proxy = ProxyConfig(
        use_isp_proxy=resolved_use_isp_proxy,
        proxy_urls=_normalize_proxy_urls(
            _coalesce(
                proxy_urls,
                _read_proxy_urls(source, ISP_PROXY_URLS_ENV_VAR),
            )
        ),
    )
    pacing = PacingConfig(
        enabled=_coalesce(
            pacing_enabled,
            _read_bool(source, PACING_ENABLED_ENV_VAR, DEFAULT_PACING_ENABLED),
        ),
        min_delay_seconds=_coalesce(
            pacing_min_seconds,
            _read_float(
                source,
                PACING_MIN_SECONDS_ENV_VAR,
                DEFAULT_PACING_MIN_SECONDS,
            ),
        ),
        max_delay_seconds=_coalesce(
            pacing_max_seconds,
            _read_float(
                source,
                PACING_MAX_SECONDS_ENV_VAR,
                DEFAULT_PACING_MAX_SECONDS,
            ),
        ),
        warmup_min_seconds=_coalesce(
            warmup_min_seconds,
            _read_float(
                source,
                WARMUP_MIN_SECONDS_ENV_VAR,
                default_warmup_min_seconds,
            ),
        ),
        warmup_max_seconds=_coalesce(
            warmup_max_seconds,
            _read_float(
                source,
                WARMUP_MAX_SECONDS_ENV_VAR,
                default_warmup_max_seconds,
            ),
        ),
    )

    return ScraperV2Config(
        browser=browser,
        crawler=crawler,
        proxy=proxy,
        pacing=pacing,
        max_posts=_coalesce(
            max_posts,
            _read_int(source, MAX_POSTS_ENV_VAR, DEFAULT_MAX_POSTS),
        ),
    )


def _coalesce[T](explicit: T | None, default: T) -> T:
    return default if explicit is None else explicit


def _is_production_environment(env: Mapping[str, str]) -> bool:
    return env.get(ENVIRONMENT_ENV_VAR, "").strip().lower() == "production"


def _read_string(
    env: Mapping[str, str],
    var_name: str,
    default: str,
) -> str:
    raw = env.get(var_name)
    if raw is None or not raw.strip():
        return default
    return raw.strip()


def _read_int(env: Mapping[str, str], var_name: str, default: int) -> int:
    raw = env.get(var_name)
    if raw is None or not raw.strip():
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise ValueError(f"{var_name} must be a valid integer.") from exc


def _read_float(env: Mapping[str, str], var_name: str, default: float) -> float:
    raw = env.get(var_name)
    if raw is None or not raw.strip():
        return default
    try:
        return float(raw)
    except ValueError as exc:
        raise ValueError(f"{var_name} must be a valid float.") from exc


def _read_bool(env: Mapping[str, str], var_name: str, default: bool) -> bool:
    raw = env.get(var_name)
    if raw is None or not raw.strip():
        return default

    value = raw.strip().lower()
    if value in {"1", "true", "t", "yes", "y", "on"}:
        return True
    if value in {"0", "false", "f", "no", "n", "off"}:
        return False
    raise ValueError(f"{var_name} must be a valid boolean.")


def _read_proxy_urls(env: Mapping[str, str], var_name: str) -> tuple[str, ...]:
    raw = env.get(var_name)
    if raw is None:
        return ()
    return _normalize_proxy_urls(raw)


def _normalize_proxy_urls(value: Iterable[str] | str | None) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        items = value.split(",")
    else:
        items = value

    return tuple(item.strip() for item in items if item and item.strip())


def _ensure_positive_int(field_name: str, value: int) -> None:
    if value <= 0:
        raise ValueError(f"{field_name} must be greater than zero.")


def _ensure_non_empty_string(field_name: str, value: str) -> None:
    if not value.strip():
        raise ValueError(f"{field_name} must not be empty.")


def _ensure_non_negative_float(field_name: str, value: float) -> None:
    if value < 0:
        raise ValueError(f"{field_name} must be zero or greater.")


__all__ = [
    "BrowserConfig",
    "CrawlerConfig",
    "ENVIRONMENT_ENV_VAR",
    "HEADLESS_ENV_VAR",
    "ISP_PROXY_URLS_ENV_VAR",
    "LOCALE_ENV_VAR",
    "MAX_CONCURRENT_ENV_VAR",
    "MAX_POSTS_ENV_VAR",
    "PACING_ENABLED_ENV_VAR",
    "PACING_MAX_SECONDS_ENV_VAR",
    "PACING_MIN_SECONDS_ENV_VAR",
    "ProxyConfig",
    "PacingConfig",
    "ScraperV2Config",
    "TIMEOUT_MS_ENV_VAR",
    "USE_ISP_PROXY_ENV_VAR",
    "WARMUP_MAX_SECONDS_ENV_VAR",
    "WARMUP_MIN_SECONDS_ENV_VAR",
    "build_scraper_v2_config",
]
