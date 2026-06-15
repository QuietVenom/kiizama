from __future__ import annotations

from dataclasses import asdict
from typing import Any

from .models import InstagramBatchScrapeRunResult
from .schemas import InstagramBatchScrapeResponse


def to_instagram_batch_scrape_response(
    run_result: InstagramBatchScrapeRunResult,
) -> InstagramBatchScrapeResponse:
    """Convert the internal v2 run result into the v2 batch response contract."""
    return InstagramBatchScrapeResponse.model_validate(
        {
            "results": _sanitize_results(run_result.results),
            "counters": asdict(run_result.counters),
            "error": run_result.error,
        }
    )


def _sanitize_results(
    results: dict[str, dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    return {
        username: _sanitize_profile_result_payload(profile_result)
        for username, profile_result in results.items()
    }


def _sanitize_profile_result_payload(
    profile_result: dict[str, Any],
) -> dict[str, Any]:
    sanitized = dict(profile_result)
    metrics = dict(sanitized.get("metrics") or {})
    metrics.pop("user", None)
    metrics.pop("recommended_users", None)
    sanitized["metrics"] = metrics
    sanitized["recommended_users"] = list(sanitized.get("recommended_users") or [])
    return sanitized


__all__ = ["to_instagram_batch_scrape_response"]
