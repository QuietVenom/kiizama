from typing import Any

import pytest

from app.features.social_media_report import service as report_service


class FakeInstagramReportGenerator:
    def __init__(self, *, template_path: str, template_name: str) -> None:
        self.template_path = template_path
        self.template_name = template_name

    def generate_html_batch(self, reports_data: list[dict[str, Any]]) -> list[str]:
        return [
            f"<html>{item['scrape']['user']['username']}</html>"
            for item in reports_data
        ]

    def generate_pdfs_from_html_batch(self, html_contents: list[str]) -> list[bytes]:
        return [content.encode("utf-8") for content in html_contents]

    def generate_pdfs_batch(self, reports_data: list[dict[str, Any]]) -> list[bytes]:
        return [
            item["scrape"]["user"]["username"].encode("utf-8") for item in reports_data
        ]


class EmptyPdfInstagramReportGenerator(FakeInstagramReportGenerator):
    def generate_pdfs_from_html_batch(self, html_contents: list[str]) -> list[bytes]:
        del html_contents
        return []

    def generate_pdfs_batch(self, reports_data: list[dict[str, Any]]) -> list[bytes]:
        del reports_data
        return []


class FakeSnapshotModel:
    def __init__(self, payload: dict[str, Any]) -> None:
        self.payload = payload

    def model_dump(self) -> dict[str, Any]:
        return self.payload


def _snapshot(username: str, snapshot_id: str) -> dict[str, Any]:
    return {
        "_id": snapshot_id,
        "profile": {
            "username": username,
            "ai_categories": ["Beauty"],
            "ai_roles": ["Creator"],
        },
        "posts": [{"posts": [{"code": "POST1"}]}],
        "reels": [{"reels": [{"code": "REEL1"}]}],
    }


def _install_snapshots(monkeypatch: pytest.MonkeyPatch, snapshots: list[Any]) -> None:
    def fake_list_profile_snapshots_full(
        *_: Any,
        **__: Any,
    ) -> list[Any]:
        return snapshots

    monkeypatch.setattr(
        report_service,
        "list_profile_snapshots_full",
        fake_list_profile_snapshots_full,
    )


def test_snapshot_to_report_data_flattens_posts_reels_and_profile_url() -> None:
    data = report_service._snapshot_to_report_data(_snapshot("creator_one", "snap-1"))

    assert data["profile_url"] == "https://www.instagram.com/creator_one/"
    assert data["scrape"]["posts"] == [{"code": "POST1"}]
    assert data["scrape"]["reels"] == [{"code": "REEL1"}]
    assert data["scrape"]["ai_categories"] == ["Beauty"]


def test_instagram_report_tuple_posts_reels_and_model_dump_snapshot_are_coerced() -> (
    None
):
    snapshot = FakeSnapshotModel(
        {
            "_id": "snap-model",
            "profile": {
                "username": "creator_model",
                "ai_categories": ("Beauty", "Fashion"),
                "ai_roles": ("Creator",),
            },
            "posts": ({"posts": ("POST1", "POST2")},),
            "reels": ({"reels": ("REEL1",)},),
        }
    )

    data = report_service._snapshot_to_report_data(snapshot)

    assert data["profile_url"] == "https://www.instagram.com/creator_model/"
    assert data["scrape"]["posts"] == ["POST1", "POST2"]
    assert data["scrape"]["reels"] == ["REEL1"]
    assert data["scrape"]["ai_categories"] == ["Beauty", "Fashion"]


@pytest.mark.anyio
async def test_generate_instagram_report_duplicate_usernames_uses_snapshot_suffix(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_snapshots(
        monkeypatch,
        [_snapshot("creator_one", "snap-a"), _snapshot("creator_one", "snap-b")],
    )
    monkeypatch.setattr(
        report_service,
        "InstagramReportGenerator",
        FakeInstagramReportGenerator,
    )

    files = await report_service.generate_instagram_report(
        object(),
        {
            "usernames": ["creator_one", "creator_one"],
            "generate_html": True,
            "generate_pdf": True,
        },
    )

    assert [file.filename for file in files] == [
        "creator_one_snap-a.html",
        "creator_one_snap-a.pdf",
        "creator_one_snap-b.html",
        "creator_one_snap-b.pdf",
    ]


@pytest.mark.anyio
async def test_generate_instagram_report_missing_username_raises_lookup_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_snapshots(monkeypatch, [_snapshot("creator_one", "snap-a")])

    with pytest.raises(LookupError, match="missing"):
        await report_service.generate_instagram_report(
            object(),
            {"usernames": ["creator_one", "missing"]},
        )


@pytest.mark.anyio
async def test_instagram_report_no_snapshots_raises_lookup_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_snapshots(monkeypatch, [])

    with pytest.raises(LookupError, match="No se encontraron snapshots"):
        await report_service.generate_instagram_report(
            object(),
            {"usernames": ["creator_one"]},
        )


@pytest.mark.anyio
async def test_instagram_report_skips_empty_or_username_less_snapshots_then_reports_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_snapshots(
        monkeypatch,
        [
            {},
            {"profile": {}},
            _snapshot("creator_one", "snap-a"),
        ],
    )

    with pytest.raises(LookupError, match="missing_creator"):
        await report_service.generate_instagram_report(
            object(),
            {"usernames": ["creator_one", "missing_creator"]},
        )


@pytest.mark.anyio
async def test_instagram_report_snapshot_without_profile_raises_value_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_snapshots(
        monkeypatch,
        [
            {
                "_id": "snap-a",
                "profile": {"username": "creator_one"},
            }
        ],
    )
    original_snapshot_to_report_data = report_service._snapshot_to_report_data

    def invalid_snapshot_to_report_data(snapshot: Any) -> dict[str, Any]:
        del snapshot
        return original_snapshot_to_report_data({"profile": {}})

    monkeypatch.setattr(
        report_service,
        "_snapshot_to_report_data",
        invalid_snapshot_to_report_data,
    )

    with pytest.raises(ValueError, match="información de perfil"):
        await report_service.generate_instagram_report(
            object(),
            {"usernames": ["creator_one"]},
        )


@pytest.mark.anyio
async def test_instagram_report_pdf_only_uses_pdf_batch_without_html(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_snapshots(monkeypatch, [_snapshot("creator_one", "snap-a")])
    monkeypatch.setattr(
        report_service,
        "InstagramReportGenerator",
        FakeInstagramReportGenerator,
    )

    files = await report_service.generate_instagram_report(
        object(),
        {"usernames": ["creator_one"], "generate_html": False, "generate_pdf": True},
    )

    assert [file.filename for file in files] == ["creator_one.pdf"]
    assert files[0].content == b"creator_one"


@pytest.mark.anyio
async def test_instagram_report_pdf_generation_missing_output_raises_value_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_snapshots(monkeypatch, [_snapshot("creator_one", "snap-a")])
    monkeypatch.setattr(
        report_service,
        "InstagramReportGenerator",
        EmptyPdfInstagramReportGenerator,
    )

    with pytest.raises(ValueError, match="No se pudo generar el PDF"):
        await report_service.generate_instagram_report(
            object(),
            {"usernames": ["creator_one"], "generate_html": True, "generate_pdf": True},
        )
