from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.api.routes import social_media_report
from app.features.social_media_report.service import ReportFile


async def _noop_publish_billing_event(*_: Any, **__: Any) -> None:
    return None


def _noop_usage_reservation(*_: Any, **__: Any) -> None:
    return None


def _valid_report_payload() -> dict[str, Any]:
    return {"usernames": ["alpha"], "generate_html": True, "generate_pdf": False}


def _install_report_success_boundary(
    monkeypatch: pytest.MonkeyPatch,
    files: list[ReportFile],
) -> None:
    async def generate_report(*_: Any, **__: Any) -> list[ReportFile]:
        return files

    monkeypatch.setattr(
        social_media_report, "generate_instagram_report", generate_report
    )
    monkeypatch.setattr(
        social_media_report, "reserve_feature_usage", _noop_usage_reservation
    )
    monkeypatch.setattr(
        social_media_report, "finalize_usage_reservation", _noop_usage_reservation
    )
    monkeypatch.setattr(
        social_media_report, "release_usage_reservation", _noop_usage_reservation
    )
    monkeypatch.setattr(
        social_media_report, "publish_billing_event", _noop_publish_billing_event
    )


def test_social_media_report_single_file_returns_download_response(
    client: TestClient,
    normal_user_token_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Arrange
    _install_report_success_boundary(
        monkeypatch,
        [
            ReportFile(
                filename="alpha.html",
                content_type="text/html",
                content=b"<html>alpha</html>",
            )
        ],
    )

    # Act
    response = client.post(
        "/api/v1/social-media-report/instagram",
        headers=normal_user_token_headers,
        json={"usernames": ["alpha"], "generate_html": True, "generate_pdf": False},
    )

    # Assert
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert 'filename="alpha.html"' in response.headers["content-disposition"]
    assert response.content == b"<html>alpha</html>"


def test_social_media_report_multiple_files_returns_zip_response(
    client: TestClient,
    normal_user_token_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Arrange
    _install_report_success_boundary(
        monkeypatch,
        [
            ReportFile(
                filename="alpha.html", content_type="text/html", content=b"alpha"
            ),
            ReportFile(filename="beta.html", content_type="text/html", content=b"beta"),
        ],
    )

    # Act
    response = client.post(
        "/api/v1/social-media-report/instagram",
        headers=normal_user_token_headers,
        json={"usernames": ["alpha", "beta"], "generate_html": True},
    )

    # Assert
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/zip")
    assert response.content.startswith(b"PK")


def test_social_media_report_invalid_format_request_returns_validation_error(
    client: TestClient,
    normal_user_token_headers: dict[str, str],
) -> None:
    # Arrange / Act
    response = client.post(
        "/api/v1/social-media-report/instagram",
        headers=normal_user_token_headers,
        json={"usernames": ["alpha"], "generate_html": False, "generate_pdf": False},
    )

    # Assert
    assert response.status_code == 422


def test_social_media_report_lookup_error_releases_reservation_and_returns_404(
    client: TestClient,
    normal_user_token_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Arrange
    calls: dict[str, Any] = {}

    async def generate_report(*_: Any, **__: Any) -> list[ReportFile]:
        raise LookupError("Snapshots missing")

    async def publish_billing_event(**kwargs: Any) -> None:
        calls.setdefault("events", []).append(kwargs["event_name"])

    monkeypatch.setattr(
        social_media_report, "generate_instagram_report", generate_report
    )
    monkeypatch.setattr(
        social_media_report,
        "reserve_feature_usage",
        lambda **kwargs: calls.setdefault("reserved", kwargs),
    )
    monkeypatch.setattr(
        social_media_report,
        "release_usage_reservation",
        lambda **kwargs: calls.setdefault("released", kwargs),
    )
    monkeypatch.setattr(
        social_media_report, "publish_billing_event", publish_billing_event
    )

    # Act
    response = client.post(
        "/api/v1/social-media-report/instagram",
        headers=normal_user_token_headers,
        json=_valid_report_payload(),
    )

    # Assert
    assert response.status_code == 404
    assert response.json() == {"detail": "Snapshots missing"}
    assert calls["released"]["metadata"] == {"error": "Snapshots missing"}
    assert calls["events"] == ["account.usage.updated"]


def test_social_media_report_value_error_releases_reservation_and_returns_400(
    client: TestClient,
    normal_user_token_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Arrange
    calls: dict[str, Any] = {}

    async def generate_report(*_: Any, **__: Any) -> list[ReportFile]:
        raise ValueError("Invalid report data")

    async def publish_billing_event(**kwargs: Any) -> None:
        calls.setdefault("events", []).append(kwargs["event_name"])

    monkeypatch.setattr(
        social_media_report, "generate_instagram_report", generate_report
    )
    monkeypatch.setattr(social_media_report, "reserve_feature_usage", lambda **_: None)
    monkeypatch.setattr(
        social_media_report,
        "release_usage_reservation",
        lambda **kwargs: calls.setdefault("released", kwargs),
    )
    monkeypatch.setattr(
        social_media_report, "publish_billing_event", publish_billing_event
    )

    # Act
    response = client.post(
        "/api/v1/social-media-report/instagram",
        headers=normal_user_token_headers,
        json=_valid_report_payload(),
    )

    # Assert
    assert response.status_code == 400
    assert response.json() == {"detail": "Invalid report data"}
    assert calls["released"]["metadata"] == {"error": "Invalid report data"}
    assert calls["events"] == ["account.usage.updated"]


def test_social_media_report_unexpected_error_releases_reservation_and_reraises(
    client: TestClient,
    normal_user_token_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Arrange
    calls: dict[str, Any] = {}

    async def generate_report(*_: Any, **__: Any) -> list[ReportFile]:
        raise RuntimeError("generator failed")

    async def publish_billing_event(**kwargs: Any) -> None:
        calls.setdefault("events", []).append(kwargs["event_name"])

    monkeypatch.setattr(
        social_media_report, "generate_instagram_report", generate_report
    )
    monkeypatch.setattr(social_media_report, "reserve_feature_usage", lambda **_: None)
    monkeypatch.setattr(
        social_media_report,
        "release_usage_reservation",
        lambda **kwargs: calls.setdefault("released", kwargs),
    )
    monkeypatch.setattr(
        social_media_report, "publish_billing_event", publish_billing_event
    )

    # Act / Assert
    with pytest.raises(RuntimeError, match="generator failed"):
        client.post(
            "/api/v1/social-media-report/instagram",
            headers=normal_user_token_headers,
            json=_valid_report_payload(),
        )
    assert "metadata" not in calls["released"]
    assert calls["events"] == ["account.usage.updated"]


def test_social_media_report_success_finalizes_usage_with_generated_file_count(
    client: TestClient,
    normal_user_token_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Arrange
    calls: dict[str, Any] = {}

    async def generate_report(*_: Any, **__: Any) -> list[ReportFile]:
        return [
            ReportFile(
                filename="alpha.html", content_type="text/html", content=b"html"
            ),
            ReportFile(
                filename="alpha.pdf", content_type="application/pdf", content=b"pdf"
            ),
        ]

    async def publish_billing_event(**kwargs: Any) -> None:
        calls.setdefault("events", []).append(kwargs["event_name"])

    monkeypatch.setattr(
        social_media_report, "generate_instagram_report", generate_report
    )
    monkeypatch.setattr(
        social_media_report,
        "reserve_feature_usage",
        lambda **kwargs: calls.setdefault("reserved", kwargs),
    )
    monkeypatch.setattr(
        social_media_report,
        "finalize_usage_reservation",
        lambda **kwargs: calls.setdefault("finalized", kwargs),
    )
    monkeypatch.setattr(
        social_media_report,
        "release_usage_reservation",
        lambda **kwargs: calls.setdefault("released", kwargs),
    )
    monkeypatch.setattr(
        social_media_report, "publish_billing_event", publish_billing_event
    )

    # Act
    response = client.post(
        "/api/v1/social-media-report/instagram",
        headers=normal_user_token_headers,
        json=_valid_report_payload(),
    )

    # Assert
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/zip")
    assert calls["reserved"]["max_units_requested"] == 1
    assert calls["reserved"]["metadata"] == {"usernames": ["alpha"]}
    assert calls["finalized"]["quantity_consumed"] == 1
    assert calls["finalized"]["metadata"] == {"generated_files": 2}
    assert "released" not in calls
    assert calls["events"] == ["account.usage.updated"]
