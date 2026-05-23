from __future__ import annotations

from dataclasses import asdict

import pytest
from kiizama_scrape_core.ig_scraper_v2.models import (
    ProfileOpenResult,
    ProfileOpenStatus,
)
from kiizama_scrape_core.ig_scraper_v2.runner import ProfileOpenRunResult

from scripts import validate_ig_v2_profiles as script


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
    assert options.json_output is False


def test_parse_args_headed_and_headless() -> None:
    assert script.parse_args(["one", "--headed"]).headless is False
    assert script.parse_args(["one", "--headless"]).headless is True


def test_build_config_use_proxy_without_url_fails_when_env_has_no_proxy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("IG_SCRAPER_V2_ISP_PROXY_URLS", raising=False)
    options = script.parse_args(["one", "--use-proxy"])

    with pytest.raises(ValueError, match="At least one proxy URL"):
        script.build_config_from_options(options)


def test_build_safe_output_excludes_storage_state_and_secrets() -> None:
    output = script.build_safe_output(
        ProfileOpenRunResult(
            success=True,
            credential_id="cred_1",
            session_message="ok",
            error=None,
            results={
                "one": ProfileOpenResult(
                    requested_username="one",
                    normalized_username="one",
                    final_url="https://www.instagram.com/one/",
                    matched_username="one",
                    status=ProfileOpenStatus.SUCCESS,
                    success=True,
                    error=None,
                )
            },
        ),
        proxy_mode="local",
        headless=False,
    )

    payload = asdict(output)
    assert payload["success"] is True
    assert payload["credential_id"] == "cred_1"
    assert payload["results"][0]["status"] == "success"
    assert "cookies" not in str(payload)
    assert "sessionid" not in str(payload)


def test_main_returns_success_exit_code(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    async def fake_run_validation(
        _options: script.ScriptOptions,
    ) -> script.SafeProfileOpenOutput:
        return script.SafeProfileOpenOutput(
            success=True,
            credential_id="cred_1",
            session_message="ok",
            error=None,
            proxy_mode="local",
            headless=True,
            results=[],
        )

    monkeypatch.setattr(script, "run_validation", fake_run_validation)

    exit_code = script.main(["one", "--json"])

    assert exit_code == script.EXIT_SUCCESS
    assert '"success": true' in capsys.readouterr().out


def test_main_returns_profile_failed_exit_code(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_run_validation(
        _options: script.ScriptOptions,
    ) -> script.SafeProfileOpenOutput:
        return script.SafeProfileOpenOutput(
            success=False,
            credential_id="cred_1",
            session_message="ok",
            error=None,
            proxy_mode="local",
            headless=True,
            results=[],
        )

    monkeypatch.setattr(script, "run_validation", fake_run_validation)

    assert script.main(["one"]) == script.EXIT_PROFILE_FAILED


def test_main_returns_config_error_exit_code(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_run_validation(
        _options: script.ScriptOptions,
    ) -> script.SafeProfileOpenOutput:
        raise ValueError("bad config")

    monkeypatch.setattr(script, "run_validation", fake_run_validation)

    assert script.main(["one"]) == script.EXIT_CONFIG_ERROR
