from unittest.mock import MagicMock, patch

from sqlmodel import select

from app.tests_pre_start import init, logger


def test_init_successful_connection() -> None:
    engine_mock = MagicMock()

    session_mock = MagicMock()
    session_factory_mock = MagicMock()
    session_factory_mock.return_value.__enter__.return_value = session_mock

    with (
        patch("app.tests_pre_start.Session", session_factory_mock),
        patch.object(logger, "info"),
        patch.object(logger, "error"),
        patch.object(logger, "warn"),
    ):
        try:
            init(engine_mock)
            connection_successful = True
        except Exception:
            connection_successful = False

        assert connection_successful, (
            "The database connection should be successful and not raise an exception."
        )

        session_factory_mock.assert_called_once_with(engine_mock)
        session_mock.exec.assert_called_once()
        statement = session_mock.exec.call_args.args[0]
        assert str(statement) == str(select(1))
