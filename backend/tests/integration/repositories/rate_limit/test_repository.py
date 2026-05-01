from __future__ import annotations

from typing import Any

import pytest

from app.features.rate_limit.keys import (
    build_rate_limit_key,
    build_rate_limit_sequence_key,
)
from app.features.rate_limit.policies import POLICIES
from app.features.rate_limit.repository import RateLimitRepository


@pytest.mark.anyio
async def test_token_bucket_consumes_capacity_and_refills(redis_client: Any) -> None:
    repository = RateLimitRepository(redis_provider=lambda: redis_client)
    rule = POLICIES.public_form_submit.rules[0]

    denied = None
    for index in range(5):
        decision = await repository.evaluate_rule(
            policy_name=POLICIES.public_form_submit.name,
            subject="203.0.113.1",
            rule=rule,
            now_ms=index,
        )
        assert decision.allowed is True
        denied = decision

    assert denied is not None
    blocked = await repository.evaluate_rule(
        policy_name=POLICIES.public_form_submit.name,
        subject="203.0.113.1",
        rule=rule,
        now_ms=10,
    )
    assert blocked.allowed is False
    assert blocked.retry_after_seconds > 0

    recovered = await repository.evaluate_rule(
        policy_name=POLICIES.public_form_submit.name,
        subject="203.0.113.1",
        rule=rule,
        now_ms=15 * 60 * 1000,
    )
    assert recovered.allowed is True
    assert (
        await redis_client.ttl(
            build_rate_limit_key(
                policy_name=POLICIES.public_form_submit.name,
                subject="203.0.113.1",
            )
        )
        > 0
    )


@pytest.mark.anyio
async def test_sliding_window_blocks_until_window_moves(redis_client: Any) -> None:
    repository = RateLimitRepository(redis_provider=lambda: redis_client)
    rule = POLICIES.public_auth_login.rules[1]

    for index in range(5):
        decision = await repository.evaluate_rule(
            policy_name=POLICIES.public_auth_login.name,
            subject="203.0.113.1:user@example.com",
            rule=rule,
            now_ms=index,
        )
        assert decision.allowed is True

    blocked = await repository.evaluate_rule(
        policy_name=POLICIES.public_auth_login.name,
        subject="203.0.113.1:user@example.com",
        rule=rule,
        now_ms=100,
    )
    assert blocked.allowed is False
    assert blocked.retry_after_seconds == 600
    assert (
        await redis_client.ttl(
            build_rate_limit_sequence_key(
                policy_name=POLICIES.public_auth_login.name,
                subject="203.0.113.1:user@example.com",
            )
        )
        > 0
    )


@pytest.mark.anyio
async def test_script_loader_falls_back_after_noscript(redis_client: Any) -> None:
    repository = RateLimitRepository(redis_provider=lambda: redis_client)
    rule = POLICIES.jobs_write.rules[0]

    decision = await repository.evaluate_rule(
        policy_name=POLICIES.jobs_write.name,
        subject="user-1",
        rule=rule,
        now_ms=0,
    )

    assert decision.allowed is True
