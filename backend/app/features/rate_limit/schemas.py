from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class RateLimitAlgorithm(str, Enum):
    TOKEN_BUCKET = "token_bucket"
    SLIDING_WINDOW = "sliding_window"


class RateLimitSubjectKind(str, Enum):
    IP = "ip"
    USER_ID = "user_id"
    EMAIL = "email"
    IP_EMAIL = "ip+email"
    IP_USERNAME = "ip+username"


class RateLimitRule(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    algorithm: RateLimitAlgorithm
    subject: RateLimitSubjectKind
    cost: int = Field(default=1, ge=1)
    capacity: int | None = Field(default=None, ge=1)
    refill_tokens: int | None = Field(default=None, ge=1)
    refill_period_seconds: int | None = Field(default=None, ge=1)
    window_seconds: int | None = Field(default=None, ge=1)
    max_requests: int | None = Field(default=None, ge=1)


class RateLimitPolicy(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    rules: tuple[RateLimitRule, ...]
    on_redis_error: Literal["fail_open", "fail_closed"]
    emit_headers: bool = True
    header_rule_index: int = Field(default=0, ge=0)


class RateLimitDecision(BaseModel):
    allowed: bool
    limit: int
    remaining: int
    retry_after_seconds: int
    reset_after_seconds: int
    rule: str
