from __future__ import annotations

from dataclasses import asdict

import pytest

from scripts import validate_ig_v2_persist as script


def test_parse_args_requires_usernames() -> None:
    with pytest.raises(SystemExit):
        script.parse_args([])


def test_parse_args_defaults() -> None:
    options = script.parse_args(["one", "two"])

    assert options.usernames == ("one", "two")
    assert options.headless is None
    assert options.use_proxy is False
    assert options.proxy_urls is None
    assert options.timeout_ms is None
    assert options.credential_id is None
    assert options.login_username is None
    assert options.max_concurrent is None
    assert options.max_posts == 12
    assert options.skip_ai is False
    assert options.json_output is False


def test_parse_args_supports_persistence_controls() -> None:
    options = script.parse_args(
        [
            "one",
            "--headed",
            "--max-concurrent",
            "2",
            "--max-posts",
            "5",
            "--skip-ai",
            "--json",
        ]
    )

    assert options.headless is False
    assert options.max_concurrent == 2
    assert options.max_posts == 5
    assert options.skip_ai is True
    assert options.json_output is True


def test_configure_runtime_secrets_from_settings_exports_openai_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setattr(script.settings, "OPENAI_API_KEY", "sk-from-settings")

    script.configure_runtime_secrets_from_settings()

    assert script.os.environ["OPENAI_API_KEY"] == "sk-from-settings"


def test_configure_runtime_secrets_from_settings_preserves_existing_openai_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-existing")
    monkeypatch.setattr(script.settings, "OPENAI_API_KEY", "sk-from-settings")

    script.configure_runtime_secrets_from_settings()

    assert script.os.environ["OPENAI_API_KEY"] == "sk-existing"


def test_build_safe_output_classifies_summary_usernames() -> None:
    output = script.build_safe_output(
        summary={
            "usernames": [
                {"username": "ok", "status": "success"},
                {"username": "fresh", "status": "skipped"},
                {"username": "missing", "status": "not_found"},
                {"username": "bad", "status": "failed", "error": "boom"},
            ],
            "counters": {
                "requested": 3,
                "successful": 1,
                "not_found": 1,
                "failed": 1,
            },
            "error": None,
        },
        proxy_mode="local",
        headless=False,
    )

    payload = asdict(output)
    assert payload["success"] is False
    assert payload["persisted_usernames"] == ["ok"]
    assert payload["skipped_usernames"] == ["fresh"]
    assert payload["not_found_usernames"] == ["missing"]
    assert payload["failed_usernames"] == ["bad"]
    assert "cookies" not in str(payload)
    assert "sessionid" not in str(payload)


def test_main_returns_success_exit_code(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    async def fake_run_validation(
        _options: script.ScriptOptions,
    ) -> script.SafePersistOutput:
        return script.SafePersistOutput(
            success=True,
            error=None,
            proxy_mode="local",
            headless=True,
            counters={"requested": 1, "successful": 1, "failed": 0, "not_found": 0},
            summary={},
            persisted_usernames=["one"],
            skipped_usernames=[],
            not_found_usernames=[],
            failed_usernames=[],
        )

    monkeypatch.setattr(script, "run_validation", fake_run_validation)

    exit_code = script.main(["one", "--json"])

    assert exit_code == script.EXIT_SUCCESS
    assert '"success": true' in capsys.readouterr().out


def test_main_returns_failed_exit_code(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_run_validation(
        _options: script.ScriptOptions,
    ) -> script.SafePersistOutput:
        return script.SafePersistOutput(
            success=False,
            error=None,
            proxy_mode="local",
            headless=True,
            counters={"requested": 1, "successful": 0, "failed": 1, "not_found": 0},
            summary={},
            persisted_usernames=[],
            skipped_usernames=[],
            not_found_usernames=[],
            failed_usernames=["one"],
        )

    monkeypatch.setattr(script, "run_validation", fake_run_validation)

    assert script.main(["one"]) == script.EXIT_SCRAPE_FAILED


def test_main_returns_config_error_exit_code(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_run_validation(
        _options: script.ScriptOptions,
    ) -> script.SafePersistOutput:
        raise ValueError("bad config")

    monkeypatch.setattr(script, "run_validation", fake_run_validation)

    assert script.main(["one"]) == script.EXIT_CONFIG_ERROR
