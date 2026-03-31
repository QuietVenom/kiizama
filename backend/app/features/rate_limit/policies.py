from __future__ import annotations

from .schemas import (
    RateLimitAlgorithm,
    RateLimitPolicy,
    RateLimitRule,
    RateLimitSubjectKind,
)


class POLICIES:
    public_auth_login = RateLimitPolicy(
        name="public_auth_login",
        on_redis_error="fail_closed",
        header_rule_index=0,
        rules=(
            RateLimitRule(
                name="ip",
                algorithm=RateLimitAlgorithm.SLIDING_WINDOW,
                subject=RateLimitSubjectKind.IP,
                max_requests=20,
                window_seconds=5 * 60,
            ),
            RateLimitRule(
                name="ip_username",
                algorithm=RateLimitAlgorithm.SLIDING_WINDOW,
                subject=RateLimitSubjectKind.IP_USERNAME,
                max_requests=5,
                window_seconds=10 * 60,
            ),
        ),
    )
    public_auth_password_recovery = RateLimitPolicy(
        name="public_auth_password_recovery",
        on_redis_error="fail_closed",
        header_rule_index=0,
        rules=(
            RateLimitRule(
                name="ip",
                algorithm=RateLimitAlgorithm.SLIDING_WINDOW,
                subject=RateLimitSubjectKind.IP,
                max_requests=5,
                window_seconds=30 * 60,
            ),
            RateLimitRule(
                name="email",
                algorithm=RateLimitAlgorithm.SLIDING_WINDOW,
                subject=RateLimitSubjectKind.EMAIL,
                max_requests=3,
                window_seconds=60 * 60,
            ),
            RateLimitRule(
                name="ip_email",
                algorithm=RateLimitAlgorithm.SLIDING_WINDOW,
                subject=RateLimitSubjectKind.IP_EMAIL,
                max_requests=2,
                window_seconds=30 * 60,
            ),
        ),
    )
    public_auth_reset_password = RateLimitPolicy(
        name="public_auth_reset_password",
        on_redis_error="fail_closed",
        header_rule_index=0,
        rules=(
            RateLimitRule(
                name="ip",
                algorithm=RateLimitAlgorithm.SLIDING_WINDOW,
                subject=RateLimitSubjectKind.IP,
                max_requests=10,
                window_seconds=15 * 60,
            ),
        ),
    )
    public_auth_signup = RateLimitPolicy(
        name="public_auth_signup",
        on_redis_error="fail_closed",
        header_rule_index=0,
        rules=(
            RateLimitRule(
                name="ip",
                algorithm=RateLimitAlgorithm.SLIDING_WINDOW,
                subject=RateLimitSubjectKind.IP,
                max_requests=5,
                window_seconds=60 * 60,
            ),
        ),
    )
    public_form_submit = RateLimitPolicy(
        name="public_form_submit",
        on_redis_error="fail_open",
        header_rule_index=0,
        rules=(
            RateLimitRule(
                name="ip",
                algorithm=RateLimitAlgorithm.TOKEN_BUCKET,
                subject=RateLimitSubjectKind.IP,
                capacity=5,
                refill_tokens=1,
                refill_period_seconds=15 * 60,
            ),
        ),
    )
    jobs_write = RateLimitPolicy(
        name="jobs_write",
        on_redis_error="fail_open",
        header_rule_index=0,
        rules=(
            RateLimitRule(
                name="user_id",
                algorithm=RateLimitAlgorithm.TOKEN_BUCKET,
                subject=RateLimitSubjectKind.USER_ID,
                capacity=12,
                refill_tokens=12,
                refill_period_seconds=60 * 60,
            ),
        ),
    )
    jobs_read = RateLimitPolicy(
        name="jobs_read",
        on_redis_error="fail_open",
        header_rule_index=0,
        rules=(
            RateLimitRule(
                name="user_id",
                algorithm=RateLimitAlgorithm.TOKEN_BUCKET,
                subject=RateLimitSubjectKind.USER_ID,
                capacity=120,
                refill_tokens=120,
                refill_period_seconds=60 * 60,
            ),
        ),
    )
    private_basic = RateLimitPolicy(
        name="private_basic",
        on_redis_error="fail_open",
        header_rule_index=0,
        rules=(
            RateLimitRule(
                name="user_id",
                algorithm=RateLimitAlgorithm.TOKEN_BUCKET,
                subject=RateLimitSubjectKind.USER_ID,
                capacity=180,
                refill_tokens=180,
                refill_period_seconds=60 * 60,
            ),
        ),
    )
    private_expensive = RateLimitPolicy(
        name="private_expensive",
        on_redis_error="fail_open",
        header_rule_index=0,
        rules=(
            RateLimitRule(
                name="user_id",
                algorithm=RateLimitAlgorithm.TOKEN_BUCKET,
                subject=RateLimitSubjectKind.USER_ID,
                capacity=20,
                refill_tokens=20,
                refill_period_seconds=60 * 60,
            ),
        ),
    )
    stream_connect = RateLimitPolicy(
        name="stream_connect",
        on_redis_error="fail_open",
        header_rule_index=0,
        rules=(
            RateLimitRule(
                name="user_id",
                algorithm=RateLimitAlgorithm.TOKEN_BUCKET,
                subject=RateLimitSubjectKind.USER_ID,
                capacity=6,
                refill_tokens=6,
                refill_period_seconds=5 * 60,
            ),
        ),
    )
