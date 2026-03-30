from collections.abc import Generator
from typing import Any, cast

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, delete

from app.core.config import settings
from app.models import (
    IgMetrics,
    IgPostsDocument,
    IgProfile,
    IgProfileSnapshot,
    IgReelsDocument,
)


@pytest.fixture(scope="module", autouse=True)
def ensure_instagram_tables(db: Session) -> Generator[None, None, None]:
    bind = db.get_bind()
    cast(Any, IgProfile).__table__.create(bind=bind, checkfirst=True)
    cast(Any, IgPostsDocument).__table__.create(bind=bind, checkfirst=True)
    cast(Any, IgReelsDocument).__table__.create(bind=bind, checkfirst=True)
    cast(Any, IgMetrics).__table__.create(bind=bind, checkfirst=True)
    cast(Any, IgProfileSnapshot).__table__.create(bind=bind, checkfirst=True)
    db.exec(delete(IgProfileSnapshot))
    db.exec(delete(IgPostsDocument))
    db.exec(delete(IgReelsDocument))
    db.exec(delete(IgMetrics))
    db.exec(delete(IgProfile))
    db.commit()
    yield
    db.exec(delete(IgProfileSnapshot))
    db.exec(delete(IgPostsDocument))
    db.exec(delete(IgReelsDocument))
    db.exec(delete(IgMetrics))
    db.exec(delete(IgProfile))
    db.commit()


def test_ig_profiles_route_uses_postgres(
    client: TestClient,
    superuser_token_headers: dict[str, str],
) -> None:
    payload = {
        "ig_id": "1234567890",
        "username": "creator_alpha",
        "full_name": "Creator Alpha",
        "biography": "Fitness creator",
        "is_private": False,
        "is_verified": True,
        "profile_pic_url": "https://cdn.example.com/creator-alpha.jpg",
        "external_url": "https://example.com/creator-alpha",
        "updated_date": "2026-03-27T12:00:00Z",
        "follower_count": 1000,
        "following_count": 100,
        "media_count": 50,
        "bio_links": [{"title": "Site", "url": "https://example.com"}],
        "ai_categories": ["Fitness"],
        "ai_roles": ["Lifestyle"],
    }

    create_response = client.post(
        f"{settings.API_V1_STR}/ig-profiles/",
        headers=superuser_token_headers,
        json=payload,
    )
    assert create_response.status_code == 201
    created = create_response.json()
    assert created["username"] == "creator_alpha"
    assert created["_id"]

    read_response = client.get(
        f"{settings.API_V1_STR}/ig-profiles/by-username/creator_alpha",
        headers=superuser_token_headers,
    )
    assert read_response.status_code == 200
    assert read_response.json()["_id"] == created["_id"]

    patch_response = client.patch(
        f"{settings.API_V1_STR}/ig-profiles/{created['_id']}",
        headers=superuser_token_headers,
        json={"biography": "Updated bio", "follower_count": 1200},
    )
    assert patch_response.status_code == 200
    assert patch_response.json()["biography"] == "Updated bio"
    assert patch_response.json()["follower_count"] == 1200

    delete_response = client.delete(
        f"{settings.API_V1_STR}/ig-profiles/{created['_id']}",
        headers=superuser_token_headers,
    )
    assert delete_response.status_code == 200
    assert delete_response.json()["_id"] == created["_id"]
