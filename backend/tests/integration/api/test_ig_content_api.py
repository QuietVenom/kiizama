from collections.abc import Callable, Generator
from typing import Any, cast

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, delete

from app.models import IgMetrics, IgPostsDocument, IgProfile, IgReelsDocument
from tests.factories.ig_content import metrics_payload, post_payload, reel_payload
from tests.factories.ig_profiles import create_ig_profile


@pytest.fixture(scope="module", autouse=True)
def ensure_instagram_content_tables(db: Session) -> Generator[None, None, None]:
    bind = db.get_bind()
    cast(Any, IgProfile).__table__.create(bind=bind, checkfirst=True)
    cast(Any, IgPostsDocument).__table__.create(bind=bind, checkfirst=True)
    cast(Any, IgReelsDocument).__table__.create(bind=bind, checkfirst=True)
    cast(Any, IgMetrics).__table__.create(bind=bind, checkfirst=True)
    db.exec(delete(IgPostsDocument))
    db.exec(delete(IgReelsDocument))
    db.exec(delete(IgMetrics))
    db.exec(delete(IgProfile))
    db.commit()
    yield
    db.exec(delete(IgPostsDocument))
    db.exec(delete(IgReelsDocument))
    db.exec(delete(IgMetrics))
    db.exec(delete(IgProfile))
    db.commit()


@pytest.mark.parametrize(
    (
        "resource_path",
        "collection_key",
        "payload_factory",
        "patch_payload",
        "replace_payload",
    ),
    [
        (
            "/api/v1/ig-posts/",
            "posts",
            post_payload,
            {"posts": [{"code": "POST2", "caption_text": "updated"}]},
            lambda **kwargs: post_payload(code="POST3", **kwargs),
        ),
        (
            "/api/v1/ig-reels/",
            "reels",
            reel_payload,
            {"reels": [{"code": "REEL2", "play_count": 200}]},
            lambda **kwargs: reel_payload(code="REEL3", **kwargs),
        ),
        (
            "/api/v1/ig-metrics/",
            "metrics",
            metrics_payload,
            {"overall_post_engagement_rate": 0.75},
            metrics_payload,
        ),
    ],
)
def test_ig_content_crud_as_superuser_persists_expected_document(
    client: TestClient,
    db: Session,
    superuser_token_headers: dict[str, str],
    resource_path: str,
    collection_key: str,
    payload_factory: Callable[..., dict[str, object]],
    patch_payload: dict[str, object],
    replace_payload: Callable[..., dict[str, object]],
) -> None:
    # Arrange
    if collection_key in {"posts", "reels"}:
        profile = create_ig_profile(db, username=f"{collection_key}-creator")
        create_payload = payload_factory(profile_id=str(profile.id))
        replacement_payload = replace_payload(profile_id=str(profile.id))
    else:
        create_payload = payload_factory()
        replacement_payload = replace_payload()

    # Act
    create_response = client.post(
        resource_path, headers=superuser_token_headers, json=create_payload
    )

    # Assert
    assert create_response.status_code == 201
    created = create_response.json()
    document_id = created["_id"]

    read_response = client.get(
        f"{resource_path}{document_id}", headers=superuser_token_headers
    )
    assert read_response.status_code == 200
    assert read_response.json()["_id"] == document_id

    list_response = client.get(resource_path, headers=superuser_token_headers)
    assert list_response.status_code == 200
    assert any(
        item["_id"] == document_id for item in list_response.json()[collection_key]
    )

    patch_response = client.patch(
        f"{resource_path}{document_id}",
        headers=superuser_token_headers,
        json=patch_payload,
    )
    assert patch_response.status_code == 200
    patched = patch_response.json()
    if collection_key == "metrics":
        assert patched["overall_post_engagement_rate"] == 0.75
    else:
        assert patched[collection_key][0]["code"].endswith("2")

    replace_response = client.put(
        f"{resource_path}{document_id}",
        headers=superuser_token_headers,
        json=replacement_payload,
    )
    assert replace_response.status_code == 200
    replaced = replace_response.json()
    if collection_key != "metrics":
        assert replaced[collection_key][0]["code"].endswith("3")

    delete_response = client.delete(
        f"{resource_path}{document_id}", headers=superuser_token_headers
    )
    assert delete_response.status_code == 200
    assert delete_response.json()["_id"] == document_id

    not_found_response = client.get(
        f"{resource_path}{document_id}", headers=superuser_token_headers
    )
    assert not_found_response.status_code == 404


@pytest.mark.parametrize(
    "resource_path",
    ["/api/v1/ig-posts/", "/api/v1/ig-reels/", "/api/v1/ig-metrics/"],
)
def test_ig_content_normal_user_is_forbidden(
    client: TestClient,
    normal_user_token_headers: dict[str, str],
    resource_path: str,
) -> None:
    # Arrange / Act
    response = client.get(resource_path, headers=normal_user_token_headers)

    # Assert
    assert response.status_code == 403
