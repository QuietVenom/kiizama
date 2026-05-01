from __future__ import annotations

from fastapi import HTTPException, status

from .constants import public_feature_code


class BillingError(HTTPException):
    pass


class BillingAccessError(BillingError):
    def __init__(
        self,
        detail: str = "No active plan is available for this user.",
    ) -> None:
        super().__init__(status_code=status.HTTP_402_PAYMENT_REQUIRED, detail=detail)


class BillingLimitExceededError(BillingError):
    def __init__(self, feature_code: str) -> None:
        super().__init__(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=(
                "Credit limit exceeded for feature "
                f"'{public_feature_code(feature_code)}'."
            ),
        )


__all__ = [
    "BillingAccessError",
    "BillingError",
    "BillingLimitExceededError",
]
