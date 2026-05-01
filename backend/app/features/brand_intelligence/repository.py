from __future__ import annotations

from collections.abc import Mapping, Sequence
from functools import partial
from typing import Any

from anyio import to_thread
from sqlmodel import Session

from app.core.db import engine
from app.crud.profile import (
    get_existing_profile_usernames,
    get_profiles_by_usernames,
)
from app.crud.profile_snapshots import list_profile_snapshots_full


def _fetch_profiles_by_usernames_in_new_session(
    usernames: list[str],
) -> list[dict[str, Any]]:
    with Session(engine) as session:
        return get_profiles_by_usernames(session, usernames)


def _fetch_existing_profile_usernames_in_new_session(usernames: list[str]) -> list[str]:
    with Session(engine) as session:
        return get_existing_profile_usernames(session, usernames)


def _fetch_snapshots_full_by_usernames_in_new_session(
    usernames: list[str],
) -> list[dict[str, Any]]:
    with Session(engine) as session:
        return list_profile_snapshots_full(
            session,
            skip=0,
            limit=max(len(usernames), 1),
            usernames=usernames,
        )


class BrandIntelligenceRepository:
    async def fetch_profiles_by_usernames(
        self,
        profiles_collection: Any,
        usernames: list[str],
    ) -> Sequence[Mapping[str, Any]]:
        del profiles_collection
        profiles = await to_thread.run_sync(
            partial(_fetch_profiles_by_usernames_in_new_session, usernames)
        )
        return [profile for profile in profiles if isinstance(profile, Mapping)]

    async def fetch_existing_profile_usernames(
        self,
        profiles_collection: Any,
        usernames: list[str],
    ) -> list[str]:
        del profiles_collection
        return await to_thread.run_sync(
            partial(_fetch_existing_profile_usernames_in_new_session, usernames)
        )

    async def fetch_snapshots_full_by_usernames(
        self,
        profile_snapshots_collection: Any,
        usernames: list[str],
    ) -> Sequence[Mapping[str, Any]]:
        del profile_snapshots_collection
        snapshots = await to_thread.run_sync(
            partial(_fetch_snapshots_full_by_usernames_in_new_session, usernames)
        )
        return [snapshot for snapshot in snapshots if isinstance(snapshot, Mapping)]


__all__ = ["BrandIntelligenceRepository"]
