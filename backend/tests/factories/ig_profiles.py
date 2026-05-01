import uuid
from datetime import UTC, datetime

from sqlmodel import Session

from app.models import IgProfile


def profile_payload(*, username: str = "alpha") -> dict[str, object]:
    return {
        "_id": str(uuid.uuid4()),
        "ig_id": f"ig-{uuid.uuid4()}",
        "username": username,
        "full_name": "Alpha Creator",
        "biography": "Creator bio",
        "follower_count": 1000,
        "following_count": 100,
        "media_count": 25,
        "updated_at": datetime.now(UTC).isoformat(),
    }


def create_ig_profile(
    db: Session,
    *,
    username: str = "creator-alpha",
) -> IgProfile:
    profile = IgProfile(
        ig_id=f"ig-{uuid.uuid4()}",
        username=username,
        full_name="Alpha Creator",
        biography="Creator bio",
        is_private=False,
        is_verified=True,
        profile_pic_url="https://cdn.example.com/alpha.jpg",
        external_url="https://example.com/alpha",
        follower_count=1000,
        following_count=100,
        media_count=25,
        bio_links=[],
        ai_categories=["Fitness"],
        ai_roles=["Creator"],
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile
