from __future__ import annotations

from sqlalchemy.engine.url import make_url


def is_safe_test_database_url(database_url: str | None) -> bool:
    if not database_url or not database_url.strip():
        return False

    try:
        url = make_url(database_url.strip())
    except Exception:
        return False

    database_name = (url.database or "").strip("/")
    host = url.host or ""
    port = url.port

    if database_name.endswith("_test"):
        return True
    if host == "postgres_test":
        return True
    if host in {"localhost", "127.0.0.1"} and port == 55432:
        return True

    return False


def assert_safe_test_database_url(database_url: str | None) -> None:
    if is_safe_test_database_url(database_url):
        return

    raise RuntimeError(
        "Refusing to run tests against a non-test database. "
        "Configure TEST_DATABASE_URL/DATABASE_URL to a dedicated test database "
        "(for example app_test on localhost:55432 or host postgres_test)."
    )


__all__ = ["assert_safe_test_database_url", "is_safe_test_database_url"]
