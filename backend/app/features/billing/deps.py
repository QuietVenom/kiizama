"""FastAPI dependencies for billing access enforcement.

Import from this module directly (`app.features.billing.deps`); it is not
re-exported from the package: `app.models` imports `billing.models`, which runs
the package `__init__`, and pulling `app.api.deps` there is a circular import.
"""

from __future__ import annotations

from app.api.deps import CurrentUser, SessionDep

from .errors import BillingAccessError
from .service import has_active_billing_access


def require_active_billing_access(
    session: SessionDep,
    current_user: CurrentUser,
) -> None:
    if not has_active_billing_access(session=session, user=current_user):
        raise BillingAccessError()


__all__ = [
    "require_active_billing_access",
]
