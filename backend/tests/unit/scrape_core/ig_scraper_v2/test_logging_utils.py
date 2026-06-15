from __future__ import annotations

from kiizama_scrape_core.ig_scraper_v2.logging_utils import (
    format_counters,
    redacted_identifier,
    redacted_login_username,
    sanitize_exception_for_log,
    sanitize_log_value,
)
from kiizama_scrape_core.ig_scraper_v2.models import BatchScrapeCounters


def test_redacted_identifier_hides_full_uuid() -> None:
    assert (
        redacted_identifier("019e5cc6-d98a-71f6-975d-bd164c313865")
        == "019e5cc6-...-bd164c313865"
    )


def test_redacted_login_username_hides_email_local_part() -> None:
    assert redacted_login_username("izco.marcos@outlook.com") == "i***@outlook.com"
    assert redacted_login_username("plain_username") == "p***"


def test_sanitize_log_value_removes_sensitive_values() -> None:
    raw = (
        "proxy=http://proxy-user:proxy-pass@proxy.example:8000 "
        "Cookie: sessionid=session-secret; csrftoken=csrf-secret "
        "Authorization: Bearer token-secret password=my-password"
    )

    sanitized = sanitize_log_value(raw)

    assert "proxy-user" not in sanitized
    assert "proxy-pass" not in sanitized
    assert "session-secret" not in sanitized
    assert "csrf-secret" not in sanitized
    assert "token-secret" not in sanitized
    assert "my-password" not in sanitized
    assert "proxy=<redacted>" in sanitized
    assert "Cookie: <redacted>" in sanitized
    assert "Authorization: <redacted>" in sanitized
    assert "password=<redacted>" in sanitized


def test_sanitize_exception_for_log_replaces_exception_args() -> None:
    exc = RuntimeError("proxy=http://user:pass@proxy.example:8000")

    sanitized = sanitize_exception_for_log(exc)

    assert "user:pass" not in sanitized
    assert str(exc) == "proxy=<redacted>"


def test_format_counters_is_stable() -> None:
    counters = BatchScrapeCounters(requested=3, successful=2, failed=1, not_found=0)

    assert format_counters(counters) == (
        "requested=3 successful=2 failed=1 not_found=0"
    )
