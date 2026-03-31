from __future__ import annotations

from fastapi import Response
from starlette.requests import Request

from .repository import RateLimitRepository
from .schemas import RateLimitDecision, RateLimitPolicy
from .subjects import resolve_subject


class RateLimitExceededError(RuntimeError):
    def __init__(
        self,
        *,
        policy: str,
        retry_after_seconds: int,
        limit: int,
        remaining: int,
        reset_after_seconds: int,
    ) -> None:
        super().__init__("Rate limit exceeded.")
        self.policy = policy
        self.retry_after_seconds = retry_after_seconds
        self.limit = limit
        self.remaining = remaining
        self.reset_after_seconds = reset_after_seconds
        self.status_code = 429


class RateLimitService:
    def __init__(self, *, repository: RateLimitRepository | None = None) -> None:
        self._repository = repository or RateLimitRepository()

    async def enforce(
        self,
        *,
        policy: RateLimitPolicy,
        request: Request,
        response: Response,
    ) -> None:
        decisions: list[RateLimitDecision | None] = []
        try:
            for rule in policy.rules:
                subject = await resolve_subject(
                    request,
                    policy=policy,
                    subject_kind=rule.subject,
                )
                if subject is None:
                    decisions.append(None)
                    continue
                decision = await self._repository.evaluate_rule(
                    policy_name=policy.name,
                    subject=subject,
                    rule=rule,
                )
                decisions.append(decision)
                if not decision.allowed:
                    raise RateLimitExceededError(
                        policy=policy.name,
                        retry_after_seconds=decision.retry_after_seconds,
                        limit=decision.limit,
                        remaining=decision.remaining,
                        reset_after_seconds=decision.reset_after_seconds,
                    )
        except RateLimitExceededError:
            if policy.emit_headers:
                header_decision = self._select_header_decision(
                    policy=policy, decisions=decisions
                )
                if header_decision is not None:
                    self._apply_headers(
                        response,
                        policy=policy,
                        decision=header_decision,
                        retry_after=header_decision.retry_after_seconds,
                    )
            raise
        except Exception as exc:
            from app.core.resilience import (
                mark_dependency_failure,
                translate_redis_exception,
            )

            translated = translate_redis_exception(exc, detail=str(exc))
            mark_dependency_failure(
                "redis",
                context=f"rate-limit:{policy.name}",
                detail=translated.detail,
                status="degraded",
                exc=exc,
            )
            if policy.on_redis_error == "fail_closed":
                raise translated from exc
            return
        else:
            from app.core.resilience import mark_dependency_success

            mark_dependency_success(
                "redis",
                context=f"rate-limit:{policy.name}",
                detail="Redis rate limit check succeeded.",
            )
            if policy.emit_headers:
                header_decision = self._select_header_decision(
                    policy=policy, decisions=decisions
                )
                if header_decision is not None:
                    self._apply_headers(
                        response,
                        policy=policy,
                        decision=header_decision,
                        retry_after=0,
                    )

    @staticmethod
    def _select_header_decision(
        *,
        policy: RateLimitPolicy,
        decisions: list[RateLimitDecision | None],
    ) -> RateLimitDecision | None:
        if not decisions:
            return None
        index = policy.header_rule_index
        if index >= len(decisions):
            return None
        return decisions[index]

    @staticmethod
    def _apply_headers(
        response: Response,
        *,
        policy: RateLimitPolicy,
        decision: RateLimitDecision,
        retry_after: int,
    ) -> None:
        response.headers["RateLimit-Limit"] = str(decision.limit)
        response.headers["RateLimit-Remaining"] = str(decision.remaining)
        response.headers["RateLimit-Reset"] = str(decision.reset_after_seconds)
        response.headers["RateLimit-Policy"] = policy.name
        if retry_after > 0:
            response.headers["Retry-After"] = str(retry_after)
