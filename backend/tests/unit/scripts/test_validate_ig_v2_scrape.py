from __future__ import annotations

from dataclasses import asdict

import pytest
from kiizama_scrape_core.ig_scraper_v2.models import (
    BatchScrapeCounters,
    InstagramBatchScrapeRunResult,
)

from scripts import validate_ig_v2_scrape as script


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
    assert options.json_output is False


def test_parse_args_max_concurrent_and_max_posts() -> None:
    options = script.parse_args(["one", "--max-concurrent", "3", "--max-posts", "5"])

    assert options.max_concurrent == 3
    assert options.max_posts == 5


def test_build_config_from_options_applies_max_concurrent() -> None:
    options = script.parse_args(["one", "--max-concurrent", "4"])

    assert script.build_config_from_options(options).crawler.max_concurrent == 4


def test_build_safe_output_excludes_storage_state_and_secrets() -> None:
    output = script.build_safe_output(
        InstagramBatchScrapeRunResult(
            success=True,
            credential_id="cred_1",
            session_message="ok",
            error=None,
            counters=BatchScrapeCounters(requested=1, successful=1),
            results={
                "one": {
                    "user": {"username": "one"},
                    "posts": [],
                    "reels": [],
                    "success": True,
                    "error": None,
                }
            },
        ),
        proxy_mode="local",
        headless=False,
    )

    payload = asdict(output)
    assert payload["success"] is True
    assert payload["counters"]["successful"] == 1
    assert "cookies" not in str(payload)
    assert "sessionid" not in str(payload)
    assert "user:pass@" not in str(payload)


def test_main_returns_success_exit_code(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    async def fake_run_validation(
        _options: script.ScriptOptions,
    ) -> script.SafeBatchScrapeOutput:
        return script.SafeBatchScrapeOutput(
            success=True,
            credential_id="cred_1",
            session_message="ok",
            error=None,
            proxy_mode="local",
            headless=True,
            counters={"requested": 1, "successful": 1, "failed": 0, "not_found": 0},
            results={},
        )

    monkeypatch.setattr(script, "run_validation", fake_run_validation)

    exit_code = script.main(["one", "--json"])

    assert exit_code == script.EXIT_SUCCESS
    assert '"success": true' in capsys.readouterr().out


def test_main_returns_scrape_failed_exit_code(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_run_validation(
        _options: script.ScriptOptions,
    ) -> script.SafeBatchScrapeOutput:
        return script.SafeBatchScrapeOutput(
            success=False,
            credential_id="cred_1",
            session_message="ok",
            error=None,
            proxy_mode="local",
            headless=True,
            counters={"requested": 1, "successful": 0, "failed": 1, "not_found": 0},
            results={},
        )

    monkeypatch.setattr(script, "run_validation", fake_run_validation)

    assert script.main(["one"]) == script.EXIT_SCRAPE_FAILED


def test_main_returns_config_error_exit_code(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_run_validation(
        _options: script.ScriptOptions,
    ) -> script.SafeBatchScrapeOutput:
        raise ValueError("bad config")

    monkeypatch.setattr(script, "run_validation", fake_run_validation)

    assert script.main(["one"]) == script.EXIT_CONFIG_ERROR
