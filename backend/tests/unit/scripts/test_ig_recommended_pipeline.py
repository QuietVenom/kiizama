from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from kiizama_scrape_core.ig_scraper_v2.schemas import (
    InstagramBatchCountersSchema,
    InstagramBatchProfileResult,
    InstagramBatchScrapeResponse,
    InstagramProfileSchema,
    InstagramSuggestedUserSchema,
)

from scripts import ig_recommended_pipeline as script


def test_parse_args_export_profiles_defaults() -> None:
    options = script.parse_args(["--export-profiles"])

    assert options.mode == "export_profiles"
    assert options.output_dir == script.DEFAULT_OUTPUT_DIR
    assert options.output_csv is None
    assert options.updated_after is None
    assert options.updated_before is None
    assert options.oldest is None
    assert options.newest is None
    assert options.batch_size == 50
    assert options.max_concurrent == 5
    assert options.max_posts == 12


def test_parse_args_discover_recommended_defaults() -> None:
    options = script.parse_args(
        ["--discover-recommended", "--input-csv", "profiles.csv"]
    )

    assert options.mode == "discover_recommended"
    assert options.input_csv == Path("profiles.csv")
    assert options.recommended_csv is None
    assert options.batch_size == 50
    assert options.max_concurrent == 5
    assert options.retry_failed is False


def test_parse_args_scrape_recommended_alias_discovers_only() -> None:
    options = script.parse_args(["--scrape-recommended", "--input-csv", "profiles.csv"])

    assert options.mode == "discover_recommended"


def test_parse_args_persist_recommended_defaults() -> None:
    options = script.parse_args(
        ["--persist-recommended", "--recommended-csv", "recommended.csv"]
    )

    assert options.mode == "persist_recommended"
    assert options.recommended_csv == Path("recommended.csv")
    assert options.input_csv is None
    assert options.batch_size == 50
    assert options.max_concurrent == 5


def test_parse_args_requires_input_csv_for_discover_recommended() -> None:
    with pytest.raises(SystemExit):
        script.parse_args(["--discover-recommended"])


def test_parse_args_requires_recommended_csv_for_persist_recommended() -> None:
    with pytest.raises(SystemExit):
        script.parse_args(["--persist-recommended"])


def test_parse_args_rejects_oldest_and_newest_together() -> None:
    with pytest.raises(SystemExit):
        script.parse_args(["--export-profiles", "--oldest", "10", "--newest", "10"])


def test_parse_args_supports_date_filters_and_scraper_controls() -> None:
    options = script.parse_args(
        [
            "--scrape-recommended",
            "--input-csv",
            "profiles.csv",
            "--updated-after",
            "2026-01-01T00:00:00Z",
            "--updated-before",
            "2026-02-01T00:00:00Z",
            "--batch-size",
            "7",
            "--max-concurrent",
            "3",
            "--headed",
            "--skip-ai",
            "--retry-failed",
            "--json",
        ]
    )

    assert options.updated_after == datetime(2026, 1, 1, tzinfo=UTC)
    assert options.updated_before == datetime(2026, 2, 1, tzinfo=UTC)
    assert options.batch_size == 7
    assert options.max_concurrent == 3
    assert options.headless is False
    assert options.skip_ai is True
    assert options.retry_failed is True
    assert options.json_output is True


def test_write_and_load_csv_rows_round_trip(tmp_path: Path) -> None:
    csv_path = tmp_path / "profiles.csv"
    rows = [
        {
            "username": "one",
            "updated_at": "2026-01-01T00:00:00+00:00",
            "status": "pending",
            "processed_at": "",
            "error": "",
        }
    ]

    script.write_csv_rows(csv_path, script.EXPORT_HEADERS, rows)

    assert script.load_csv_rows(csv_path, script.EXPORT_HEADERS) == rows


def test_upsert_recommended_rows_deduplicates_and_merges_sources() -> None:
    rows = [
        {
            "username": "related",
            "source_usernames": "source_one",
            "status": "pending",
            "discovered_at": "2026-01-01T00:00:00+00:00",
            "processed_at": "",
            "error": "",
        }
    ]

    added = script.upsert_recommended_rows(
        rows,
        source_username="source_two",
        recommended_usernames=["@Related", "new_one", ""],
        discovered_at="2026-01-02T00:00:00+00:00",
    )

    assert added == 1
    assert rows[0]["username"] == "related"
    assert rows[0]["source_usernames"] == "source_one|source_two"
    assert rows[1]["username"] == "new_one"
    assert rows[1]["source_usernames"] == "source_two"
    assert rows[1]["status"] == "pending"


def test_build_export_statement_uses_oldest_order_and_limit() -> None:
    options = script.parse_args(["--export-profiles", "--oldest", "5"])

    sql = str(script.build_export_statement(options))

    assert "ORDER BY" in sql
    assert "updated_at ASC" in sql
    assert "LIMIT" in sql


def test_build_export_statement_uses_newest_order_and_limit() -> None:
    options = script.parse_args(["--export-profiles", "--newest", "5"])

    sql = str(script.build_export_statement(options))

    assert "ORDER BY" in sql
    assert "updated_at DESC" in sql
    assert "LIMIT" in sql


def test_export_profiles_to_csv_writes_pending_rows(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output_csv = tmp_path / "profiles.csv"
    options = script.parse_args(["--export-profiles", "--output-csv", str(output_csv)])
    records = [
        ("Beta", datetime(2026, 1, 2, tzinfo=UTC)),
        ("alpha", datetime(2026, 1, 1, tzinfo=UTC)),
    ]

    class FakeResult:
        def all(self) -> list[tuple[str, datetime]]:
            return records

    class FakeSession:
        def __init__(self, _engine: Any) -> None:
            pass

        def __enter__(self) -> FakeSession:
            return self

        def __exit__(self, *_args: Any) -> None:
            return None

        def exec(self, _statement: Any) -> FakeResult:
            return FakeResult()

    monkeypatch.setattr(script, "ping_postgres", lambda: None)
    monkeypatch.setattr(script, "Session", FakeSession)

    output = script.export_profiles_to_csv(options)

    rows = script.load_csv_rows(output_csv, script.EXPORT_HEADERS)
    assert output.success is True
    assert output.exported_count == 2
    assert [row["username"] for row in rows] == ["beta", "alpha"]
    assert {row["status"] for row in rows} == {"pending"}


@pytest.mark.anyio
async def test_scrape_recommended_missing_input_csv_raises_file_not_found(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    options = script.parse_args(
        [
            "--scrape-recommended",
            "--input-csv",
            str(tmp_path / "missing.csv"),
            "--recommended-csv",
            str(tmp_path / "recommended.csv"),
        ]
    )

    monkeypatch.setattr(script, "ping_postgres", lambda: None)
    monkeypatch.setattr(script, "configure_runtime_secrets_from_settings", lambda: None)

    with pytest.raises(FileNotFoundError):
        await script.discover_recommended(options)


def _profile_result(
    *,
    username: str,
    recommended: list[str] | None = None,
    success: bool = True,
    error: str | None = None,
) -> InstagramBatchProfileResult:
    return InstagramBatchProfileResult(
        user=InstagramProfileSchema(username=username, id=f"ig-{username}"),
        recommended_users=[
            InstagramSuggestedUserSchema(username=item) for item in (recommended or [])
        ],
        success=success,
        error=error,
    )


@pytest.mark.anyio
async def test_discover_recommended_writes_only_missing_recommended_usernames(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    input_csv = tmp_path / "profiles.csv"
    recommended_csv = tmp_path / "recommended.csv"
    script.write_csv_rows(
        input_csv,
        script.EXPORT_HEADERS,
        [
            {
                "username": "source_one",
                "updated_at": "2026-01-01T00:00:00+00:00",
                "status": "pending",
                "processed_at": "",
                "error": "",
            },
            {
                "username": "source_two",
                "updated_at": "2026-01-02T00:00:00+00:00",
                "status": "pending",
                "processed_at": "",
                "error": "",
            },
        ],
    )
    options = script.parse_args(
        [
            "--discover-recommended",
            "--input-csv",
            str(input_csv),
            "--recommended-csv",
            str(recommended_csv),
            "--batch-size",
            "2",
        ]
    )
    calls: list[list[str]] = []

    async def fake_run_runner_response(
        *,
        options: script.ScriptOptions,
        usernames: list[str],
    ) -> InstagramBatchScrapeResponse:
        del options
        calls.append(usernames)
        if usernames == ["source_one", "source_two"]:
            return InstagramBatchScrapeResponse(
                results={
                    "source_one": _profile_result(
                        username="source_one",
                        recommended=[
                            "recommended_one",
                            "recommended_two",
                            "existing_profile",
                        ],
                    ),
                    "source_two": _profile_result(
                        username="source_two",
                        recommended=["recommended_two", "existing_profile"],
                    ),
                },
                counters=InstagramBatchCountersSchema(
                    requested=2,
                    successful=2,
                ),
            )
        raise AssertionError(f"unexpected usernames {usernames}")

    monkeypatch.setattr(script, "ping_postgres", lambda: None)
    monkeypatch.setattr(script, "configure_runtime_secrets_from_settings", lambda: None)
    monkeypatch.setattr(script, "run_runner_response", fake_run_runner_response)
    monkeypatch.setattr(
        script,
        "get_existing_profile_usernames",
        lambda _usernames: {"existing_profile"},
    )

    output = await script.discover_recommended(options)

    export_rows = script.load_csv_rows(input_csv, script.EXPORT_HEADERS)
    recommended_rows = script.load_csv_rows(recommended_csv, script.RECOMMENDED_HEADERS)
    assert output.success is True
    assert calls == [["source_one", "source_two"]]
    assert output.discovery_counters["skipped_existing"] == 1
    assert output.discovery_counters["added_recommended"] == 2
    assert [row["status"] for row in export_rows] == ["done", "done"]
    assert [row["username"] for row in recommended_rows] == [
        "recommended_one",
        "recommended_two",
    ]
    assert recommended_rows[1]["source_usernames"] == "source_one|source_two"
    assert [row["status"] for row in recommended_rows] == ["pending", "pending"]


@pytest.mark.anyio
async def test_persist_recommended_scrapes_and_persists_recommended_csv(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    recommended_csv = tmp_path / "recommended.csv"
    script.write_csv_rows(
        recommended_csv,
        script.RECOMMENDED_HEADERS,
        [
            {
                "username": "recommended_one",
                "source_usernames": "source_one",
                "status": "pending",
                "discovered_at": "2026-01-01T00:00:00+00:00",
                "processed_at": "",
                "error": "",
            },
            {
                "username": "recommended_two",
                "source_usernames": "source_one|source_two",
                "status": "pending",
                "discovered_at": "2026-01-01T00:00:00+00:00",
                "processed_at": "",
                "error": "",
            },
        ],
    )
    options = script.parse_args(
        [
            "--persist-recommended",
            "--recommended-csv",
            str(recommended_csv),
            "--batch-size",
            "2",
            "--skip-ai",
        ]
    )
    calls: list[list[str]] = []
    persisted_batches: list[list[str]] = []

    async def fake_run_runner_response(
        *,
        options: script.ScriptOptions,
        usernames: list[str],
    ) -> InstagramBatchScrapeResponse:
        del options
        calls.append(usernames)
        return InstagramBatchScrapeResponse(
            results={
                username: _profile_result(username=username) for username in usernames
            },
            counters=InstagramBatchCountersSchema(
                requested=len(usernames),
                successful=len(usernames),
            ),
        )

    async def fake_persist_scrape_results_to_db(
        response: InstagramBatchScrapeResponse,
        *,
        persistence: Any,
    ) -> InstagramBatchScrapeResponse:
        del persistence
        persisted_batches.append(list(response.results))
        return response

    class FakeSession:
        def __init__(self, _engine: Any) -> None:
            pass

        def __enter__(self) -> FakeSession:
            return self

        def __exit__(self, *_args: Any) -> None:
            return None

    monkeypatch.setattr(script, "ping_postgres", lambda: None)
    monkeypatch.setattr(script, "configure_runtime_secrets_from_settings", lambda: None)
    monkeypatch.setattr(script, "run_runner_response", fake_run_runner_response)
    monkeypatch.setattr(
        script,
        "persist_scrape_results_to_db",
        fake_persist_scrape_results_to_db,
    )
    monkeypatch.setattr(script, "Session", FakeSession)
    monkeypatch.setattr(script, "build_persistence", lambda _session: object())

    output = await script.persist_recommended(options)

    recommended_rows = script.load_csv_rows(recommended_csv, script.RECOMMENDED_HEADERS)
    assert output.success is True
    assert calls == [["recommended_one", "recommended_two"]]
    assert persisted_batches == [["recommended_one", "recommended_two"]]
    assert [row["status"] for row in recommended_rows] == ["done", "done"]


@pytest.mark.anyio
async def test_discover_recommended_retry_failed_includes_failed_rows(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    input_csv = tmp_path / "profiles.csv"
    recommended_csv = tmp_path / "recommended.csv"
    script.write_csv_rows(
        input_csv,
        script.EXPORT_HEADERS,
        [
            {
                "username": "source_one",
                "updated_at": "2026-01-01T00:00:00+00:00",
                "status": "failed",
                "processed_at": "2026-01-01T01:00:00+00:00",
                "error": "temporary",
            }
        ],
    )
    options = script.parse_args(
        [
            "--scrape-recommended",
            "--input-csv",
            str(input_csv),
            "--recommended-csv",
            str(recommended_csv),
            "--retry-failed",
            "--skip-ai",
        ]
    )
    calls: list[list[str]] = []

    async def fake_run_runner_response(
        *,
        options: script.ScriptOptions,
        usernames: list[str],
    ) -> InstagramBatchScrapeResponse:
        del options
        calls.append(usernames)
        return InstagramBatchScrapeResponse(
            results={
                "source_one": _profile_result(
                    username="source_one",
                    recommended=["recommended_one"],
                )
            },
            counters=InstagramBatchCountersSchema(
                requested=len(usernames),
                successful=len(usernames),
            ),
        )

    monkeypatch.setattr(script, "ping_postgres", lambda: None)
    monkeypatch.setattr(script, "configure_runtime_secrets_from_settings", lambda: None)
    monkeypatch.setattr(script, "run_runner_response", fake_run_runner_response)
    monkeypatch.setattr(
        script, "get_existing_profile_usernames", lambda _usernames: set()
    )

    output = await script.discover_recommended(options)

    assert output.success is True
    assert calls == [["source_one"]]
    assert script.load_csv_rows(input_csv, script.EXPORT_HEADERS)[0]["status"] == "done"
