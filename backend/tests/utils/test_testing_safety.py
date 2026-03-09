from app.core.testing_safety import (
    assert_safe_test_database_url,
    is_safe_test_database_url,
)


def test_is_safe_test_database_url_accepts_local_test_db() -> None:
    assert is_safe_test_database_url(
        "postgresql+psycopg://postgres:postgres@localhost:55432/app_test"
    )


def test_is_safe_test_database_url_accepts_docker_test_db() -> None:
    assert is_safe_test_database_url(
        "postgresql+psycopg://postgres:postgres@postgres_test:5432/app_test"
    )


def test_assert_safe_test_database_url_rejects_dev_db() -> None:
    try:
        assert_safe_test_database_url(
            "postgresql+psycopg://admin:secret@dev-host:5432/dev_kiizama_db"
        )
        rejected = False
    except RuntimeError:
        rejected = True

    assert rejected
