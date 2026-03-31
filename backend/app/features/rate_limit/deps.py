from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Annotated

from fastapi import Depends, Request, Response

from app.core.config import settings

from .schemas import RateLimitPolicy
from .service import RateLimitService


def get_rate_limit_service() -> RateLimitService:
    return RateLimitService()


RateLimitServiceDep = Annotated[RateLimitService, Depends(get_rate_limit_service)]


def rate_limit(policy: RateLimitPolicy) -> Callable[..., Awaitable[None]]:
    async def dependency(
        request: Request,
        response: Response,
        service: RateLimitServiceDep,
    ) -> None:
        if not settings.RATE_LIMIT_ENABLED:
            return
        await service.enforce(policy=policy, request=request, response=response)

    return dependency
