from unittest.mock import MagicMock, patch

from sqlmodel import select

from app import backend_pre_start, initial_data, tests_pre_start


def _assert_init_executes_select_one(
    *,
    init_path: str,
    init_function,
) -> None:
    engine_mock = MagicMock()
    session_mock = MagicMock()
    session_factory_mock = MagicMock()
    session_factory_mock.return_value.__enter__.return_value = session_mock

    with patch(init_path, session_factory_mock):
        init_function(engine_mock)

    session_factory_mock.assert_called_once_with(engine_mock)
    session_mock.exec.assert_called_once()
    statement = session_mock.exec.call_args.args[0]
    assert str(statement) == str(select(1))


def test_backend_pre_start_init_executes_select_one() -> None:
    _assert_init_executes_select_one(
        init_path="app.backend_pre_start.Session",
        init_function=backend_pre_start.init,
    )


def test_tests_pre_start_init_executes_select_one() -> None:
    _assert_init_executes_select_one(
        init_path="app.tests_pre_start.Session",
        init_function=tests_pre_start.init,
    )


def test_tests_pre_start_main_checks_database_safety_before_init() -> None:
    calls: list[str] = []

    with (
        patch(
            "app.tests_pre_start.assert_safe_test_database_url",
            side_effect=lambda _url: calls.append("safety"),
        ) as safety,
        patch(
            "app.tests_pre_start.init", side_effect=lambda _engine: calls.append("init")
        ),
    ):
        tests_pre_start.main()

    safety.assert_called_once()
    assert calls == ["safety", "init"]


def test_backend_pre_start_main_runs_init_with_engine() -> None:
    with patch("app.backend_pre_start.init") as init:
        backend_pre_start.main()

    init.assert_called_once_with(backend_pre_start.engine)


def test_initial_data_init_runs_init_db_inside_session() -> None:
    session_mock = MagicMock()
    session_factory_mock = MagicMock()
    session_factory_mock.return_value.__enter__.return_value = session_mock

    with (
        patch("app.initial_data.Session", session_factory_mock),
        patch("app.initial_data.init_db") as init_db,
    ):
        initial_data.init()

    session_factory_mock.assert_called_once_with(initial_data.engine)
    init_db.assert_called_once_with(session_mock)


def test_initial_data_main_invokes_init() -> None:
    with patch("app.initial_data.init") as init:
        initial_data.main()

    init.assert_called_once_with()
