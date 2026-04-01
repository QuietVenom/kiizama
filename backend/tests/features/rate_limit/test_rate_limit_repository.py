from __future__ import annotations

import asyncio

from app.features.rate_limit.keys import (
    build_rate_limit_key,
    build_rate_limit_sequence_key,
)
from app.features.rate_limit.policies import POLICIES
from app.features.rate_limit.repository import RateLimitRepository
from tests.features.rate_limit.fakes import EvalShaFakeRedis


def _run(coro):
    return asyncio.run(coro)


def test_token_bucket_consumes_capacity_and_refills() -> None:
    redis = EvalShaFakeRedis()
    repository = RateLimitRepository(redis_provider=lambda: redis)
    rule = POLICIES.public_form_submit.rules[0]

    denied = None
    for index in range(5):
        decision = _run(
            repository.evaluate_rule(
                policy_name=POLICIES.public_form_submit.name,
                subject="203.0.113.1",
                rule=rule,
                now_ms=index,
            )
        )
        assert decision.allowed is True
        denied = decision

    assert denied is not None
    blocked = _run(
        repository.evaluate_rule(
            policy_name=POLICIES.public_form_submit.name,
            subject="203.0.113.1",
            rule=rule,
            now_ms=10,
        )
    )
    assert blocked.allowed is False
    assert blocked.retry_after_seconds > 0

    recovered = _run(
        repository.evaluate_rule(
            policy_name=POLICIES.public_form_submit.name,
            subject="203.0.113.1",
            rule=rule,
            now_ms=15 * 60 * 1000,
        )
    )
    assert recovered.allowed is True
    assert (
        _run(
            redis.ttl(
                build_rate_limit_key(
                    policy_name=POLICIES.public_form_submit.name,
                    subject="203.0.113.1",
                )
            )
        )
        > 0
    )


def test_sliding_window_blocks_until_window_moves() -> None:
    redis = EvalShaFakeRedis()
    repository = RateLimitRepository(redis_provider=lambda: redis)
    rule = POLICIES.public_auth_login.rules[1]

    for index in range(5):
        decision = _run(
            repository.evaluate_rule(
                policy_name=POLICIES.public_auth_login.name,
                subject="203.0.113.1:user@example.com",
                rule=rule,
                now_ms=index,
            )
        )
        assert decision.allowed is True

    blocked = _run(
        repository.evaluate_rule(
            policy_name=POLICIES.public_auth_login.name,
            subject="203.0.113.1:user@example.com",
            rule=rule,
            now_ms=100,
        )
    )
    assert blocked.allowed is False
    assert blocked.retry_after_seconds == 600
    assert (
        _run(
            redis.ttl(
                build_rate_limit_sequence_key(
                    policy_name=POLICIES.public_auth_login.name,
                    subject="203.0.113.1:user@example.com",
                )
            )
        )
        > 0
    )


def test_script_loader_falls_back_after_noscript() -> None:
    redis = EvalShaFakeRedis()
    repository = RateLimitRepository(redis_provider=lambda: redis)
    rule = POLICIES.jobs_write.rules[0]

    decision = _run(
        repository.evaluate_rule(
            policy_name=POLICIES.jobs_write.name,
            subject="user-1",
            rule=rule,
            now_ms=0,
        )
    )

    assert decision.allowed is True
