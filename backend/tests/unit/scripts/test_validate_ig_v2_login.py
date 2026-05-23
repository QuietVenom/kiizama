from __future__ import annotations

from dataclasses import asdict
from typing import Any

import pytest
from kiizama_scrape_core.ig_scraper_v2.classes import (
    CredentialCandidate,
    SessionValidationResult,
)

from scripts import validate_ig_v2_login as script


class FakeStore:
    def __init__(self, credentials: list[CredentialCandidate]) -> None:
        self.credentials = credentials
        self.persisted: list[tuple[str, dict[str, Any]]] = []

    async def list_credentials(self, *, limit: int) -> list[CredentialCandidate]:
        return self.credentials[:limit]

    def decrypt_password(self, encrypted_password: str) -> str:
        return encrypted_password

    async def persist_session(
        self,
        credential_id: str,
        state: dict[str, Any],
    ) -> bool:
        self.persisted.append((credential_id, state))
        return True


def test_parse_args_defaults() -> None:
    options = script.parse_args([])

    assert options.headless is None
    assert options.use_proxy is False
    assert options.proxy_urls is None
    assert options.timeout_ms is None
    assert options.credential_id is None
    assert options.login_username is None
    assert options.json_output is False


def test_parse_args_headed_and_headless() -> None:
    assert script.parse_args(["--headed"]).headless is False
    assert script.parse_args(["--headless"]).headless is True


def test_build_config_use_proxy_without_url_fails_when_env_has_no_proxy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("IG_SCRAPER_V2_ISP_PROXY_URLS", raising=False)
    options = script.parse_args(["--use-proxy"])

    with pytest.raises(ValueError, match="At least one proxy URL"):
        script.build_config_from_options(options)


def test_build_config_use_proxy_accepts_repeated_proxy_urls() -> None:
    options = script.parse_args(
        [
            "--use-proxy",
            "--proxy-url",
            "http://proxy-one.example:8000",
            "--proxy-url",
            "http://proxy-two.example:8000",
        ]
    )

    config = script.build_config_from_options(options)

    assert config.proxy.use_isp_proxy is True
    assert config.proxy.proxy_urls == (
        "http://proxy-one.example:8000",
        "http://proxy-two.example:8000",
    )


@pytest.mark.anyio
async def test_filtered_credentials_store_filters_by_credential_id() -> None:
    store = script.FilteredInstagramCredentialsStore(
        FakeStore(
            [
                CredentialCandidate(
                    id="cred_1",
                    login_username="one",
                    encrypted_password="pass",
                    session=None,
                ),
                CredentialCandidate(
                    id="cred_2",
                    login_username="two",
                    encrypted_password="pass",
                    session=None,
                ),
            ]
        ),
        credential_id="cred_2",
    )

    credentials = await store.list_credentials(limit=20)

    assert [credential.id for credential in credentials] == ["cred_2"]


@pytest.mark.anyio
async def test_filtered_credentials_store_filters_by_login_username() -> None:
    store = script.FilteredInstagramCredentialsStore(
        FakeStore(
            [
                CredentialCandidate(
                    id="cred_1",
                    login_username="First.User",
                    encrypted_password="pass",
                    session=None,
                ),
                CredentialCandidate(
                    id="cred_2",
                    login_username="second.user",
                    encrypted_password="pass",
                    session=None,
                ),
            ]
        ),
        login_username=" first.user ",
    )

    credentials = await store.list_credentials(limit=20)

    assert [credential.id for credential in credentials] == ["cred_1"]


def test_build_safe_output_excludes_storage_state_and_secrets() -> None:
    result = SessionValidationResult(
        success=True,
        credential_id="cred_1",
        storage_state={"cookies": [{"name": "sessionid", "value": "secret"}]},
        message="ok",
        error=None,
    )

    output = script.build_safe_output(
        result,
        proxy_mode="local",
        headless=False,
    )

    payload = asdict(output)
    assert payload == {
        "success": True,
        "credential_id": "cred_1",
        "message": "ok",
        "error": None,
        "proxy_mode": "local",
        "headless": False,
        "storage_state_present": True,
    }
    assert "secret" not in str(payload)
    assert "sessionid" not in str(payload)


def test_main_returns_success_exit_code(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    async def fake_run_validation(
        _options: script.ScriptOptions,
    ) -> script.SafeLoginValidationOutput:
        return script.SafeLoginValidationOutput(
            success=True,
            credential_id="cred_1",
            message="ok",
            error=None,
            proxy_mode="local",
            headless=True,
            storage_state_present=True,
        )

    monkeypatch.setattr(script, "run_validation", fake_run_validation)

    exit_code = script.main(["--json"])

    assert exit_code == script.EXIT_SUCCESS
    assert '"success": true' in capsys.readouterr().out


def test_main_returns_validation_failed_exit_code(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_run_validation(
        _options: script.ScriptOptions,
    ) -> script.SafeLoginValidationOutput:
        return script.SafeLoginValidationOutput(
            success=False,
            credential_id="cred_1",
            message="failed",
            error="Login failed",
            proxy_mode="local",
            headless=True,
            storage_state_present=False,
        )

    monkeypatch.setattr(script, "run_validation", fake_run_validation)

    assert script.main([]) == script.EXIT_VALIDATION_FAILED


def test_main_returns_config_error_exit_code(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_run_validation(
        _options: script.ScriptOptions,
    ) -> script.SafeLoginValidationOutput:
        raise ValueError("bad config")

    monkeypatch.setattr(script, "run_validation", fake_run_validation)

    assert script.main([]) == script.EXIT_CONFIG_ERROR
