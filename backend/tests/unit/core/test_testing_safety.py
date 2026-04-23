import pytest

from app.core.testing_safety import (
    assert_safe_test_database_url,
    is_safe_test_database_url,
)


@pytest.mark.parametrize(
    "database_url",
    [
        "postgresql+psycopg://postgres:postgres@localhost:55432/app",
        "postgresql+psycopg://postgres:postgres@localhost:5432/app_test",
        "postgresql+psycopg://postgres:postgres@postgres_test:5432/app",
    ],
)
def test_is_safe_test_database_url_accepts_known_test_boundaries(
    database_url: str,
) -> None:
    assert is_safe_test_database_url(database_url) is True


@pytest.mark.parametrize(
    "database_url",
    [
        None,
        "",
        "not-a-url",
        "postgresql+psycopg://admin:secret@dev-host:5432/dev_kiizama_db",
    ],
)
def test_is_safe_test_database_url_rejects_unsafe_or_invalid_urls(
    database_url: str | None,
) -> None:
    assert is_safe_test_database_url(database_url) is False


def test_assert_safe_test_database_url_raises_for_unsafe_url() -> None:
    with pytest.raises(RuntimeError, match="Refusing to run tests"):
        assert_safe_test_database_url(
            "postgresql+psycopg://admin:secret@dev-host:5432/dev_kiizama_db"
        )
