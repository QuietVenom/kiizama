from __future__ import annotations

from typing import Any

import pytest
from kiizama_scrape_core.ig_scraper_v2.profile_scraper import (
    extract_user_info_from_scripts,
)


class FakePage:
    def __init__(self, payload: Any) -> None:
        self.payload = payload

    async def evaluate(self, _script: str) -> Any:
        return self.payload


@pytest.mark.anyio
async def test_extract_user_info_from_scripts_keeps_legacy_entry_data_fallback() -> (
    None
):
    page = FakePage(
        {
            "entry_data": {
                "ProfilePage": [
                    {
                        "graphql": {
                            "user": {
                                "username": "therock",
                                "follower_count": 400,
                            }
                        }
                    }
                ]
            }
        }
    )

    user_info = await extract_user_info_from_scripts(
        page,
        target_username="therock",
    )

    assert user_info is not None
    assert user_info["follower_count"] == 400


@pytest.mark.anyio
async def test_extract_user_info_from_scripts_keeps_broader_json_script_fallback() -> (
    None
):
    page = FakePage(
        [
            {
                "props": {
                    "user": {
                        "username": "therock",
                        "follower_count": 400,
                    }
                }
            }
        ]
    )

    user_info = await extract_user_info_from_scripts(
        page,
        target_username="therock",
    )

    assert user_info is not None
    assert user_info["username"] == "therock"
