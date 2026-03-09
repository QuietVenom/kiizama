from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from app.crud.profile import (
    get_existing_profile_usernames,
    get_profiles_by_usernames,
)
from app.crud.profile_snapshots import list_profile_snapshots_full


class BrandIntelligenceRepository:
    async def fetch_profiles_by_usernames(
        self,
        profiles_collection: Any,
        usernames: list[str],
    ) -> Sequence[Mapping[str, Any]]:
        profiles = await get_profiles_by_usernames(profiles_collection, usernames)
        return [profile for profile in profiles if isinstance(profile, Mapping)]

    async def fetch_existing_profile_usernames(
        self,
        profiles_collection: Any,
        usernames: list[str],
    ) -> list[str]:
        return await get_existing_profile_usernames(profiles_collection, usernames)

    async def fetch_snapshots_full_by_usernames(
        self,
        profile_snapshots_collection: Any,
        usernames: list[str],
    ) -> Sequence[Mapping[str, Any]]:
        snapshots = await list_profile_snapshots_full(
            profile_snapshots_collection,
            skip=0,
            limit=max(len(usernames), 1),
            usernames=usernames,
        )
        return [snapshot for snapshot in snapshots if isinstance(snapshot, Mapping)]


__all__ = ["BrandIntelligenceRepository"]
