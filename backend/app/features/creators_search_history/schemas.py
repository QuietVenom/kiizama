from __future__ import annotations

import re
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9._]{1,30}$")
CreatorsSearchHistorySource = Literal["direct-search", "ig-scrape-job"]


def normalize_ready_usernames(usernames: list[str]) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()

    for raw_username in usernames:
        username = raw_username.strip().removeprefix("@").lower()
        if not username:
            continue
        if not USERNAME_PATTERN.fullmatch(username):
            raise ValueError("ready_usernames contains an invalid Instagram username.")
        if username in seen:
            continue
        seen.add(username)
        normalized.append(username)

    return normalized


class CreatorsSearchHistoryItem(BaseModel):
    id: str
    created_at: datetime
    source: CreatorsSearchHistorySource
    job_id: str | None = None
    ready_usernames: list[str] = Field(default_factory=list)

    model_config = ConfigDict(str_strip_whitespace=True)


class CreatorsSearchHistoryListResponse(BaseModel):
    items: list[CreatorsSearchHistoryItem] = Field(default_factory=list)
    count: int = 0


class CreatorsSearchHistoryCreateRequest(BaseModel):
    source: CreatorsSearchHistorySource
    job_id: str | None = None
    ready_usernames: list[str] = Field(
        ...,
        min_length=1,
        max_length=50,
    )

    model_config = ConfigDict(str_strip_whitespace=True)

    @model_validator(mode="after")
    def validate_request(self) -> CreatorsSearchHistoryCreateRequest:
        self.ready_usernames = normalize_ready_usernames(self.ready_usernames)
        if not self.ready_usernames:
            raise ValueError("ready_usernames cannot be empty.")

        if self.source == "ig-scrape-job":
            if not self.job_id:
                raise ValueError("job_id is required for ig-scrape-job entries.")
        elif self.job_id is not None:
            raise ValueError("job_id must be null for direct-search entries.")

        return self


__all__ = [
    "CreatorsSearchHistoryCreateRequest",
    "CreatorsSearchHistoryItem",
    "CreatorsSearchHistoryListResponse",
    "CreatorsSearchHistorySource",
    "normalize_ready_usernames",
]
