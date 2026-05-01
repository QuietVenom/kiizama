from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Header, Request

from app.api.deps import CurrentUser, SessionDep
from app.features.billing import (
    build_billing_summary,
    create_checkout_session,
    create_portal_session,
    list_billing_notice_public,
    mark_billing_notice_status,
    process_stripe_webhook,
    publish_billing_event,
    verify_stripe_signature,
)
from app.features.billing.schemas import (
    BillingNoticeCollectionPublic,
    BillingNoticePublic,
    BillingSessionPublic,
    BillingSummaryPublic,
    BillingWebhookReceipt,
)
from app.features.rate_limit import POLICIES, rate_limit

router = APIRouter(prefix="/billing", tags=["billing"])


@router.get(
    "/me",
    response_model=BillingSummaryPublic,
    dependencies=[Depends(rate_limit(POLICIES.private_basic))],
)
def read_billing_me(
    session: SessionDep,
    current_user: CurrentUser,
) -> BillingSummaryPublic:
    return build_billing_summary(session=session, user_id=current_user.id)


@router.get(
    "/notices",
    response_model=BillingNoticeCollectionPublic,
    dependencies=[Depends(rate_limit(POLICIES.private_basic))],
)
def read_billing_notices(
    session: SessionDep,
    current_user: CurrentUser,
) -> BillingNoticeCollectionPublic:
    return BillingNoticeCollectionPublic(
        data=list_billing_notice_public(session=session, user_id=current_user.id)
    )


@router.post(
    "/checkout-session",
    response_model=BillingSessionPublic,
    dependencies=[Depends(rate_limit(POLICIES.private_basic))],
)
async def create_checkout_session_endpoint(
    session: SessionDep,
    current_user: CurrentUser,
) -> BillingSessionPublic:
    url = await create_checkout_session(session=session, user=current_user)
    return BillingSessionPublic(url=url)


@router.post(
    "/portal-session",
    response_model=BillingSessionPublic,
    dependencies=[Depends(rate_limit(POLICIES.private_basic))],
)
async def create_portal_session_endpoint(
    session: SessionDep,
    current_user: CurrentUser,
) -> BillingSessionPublic:
    url = await create_portal_session(session=session, user=current_user)
    return BillingSessionPublic(url=url)


@router.post(
    "/notices/{notice_id}/read",
    response_model=BillingNoticePublic,
    dependencies=[Depends(rate_limit(POLICIES.private_basic))],
)
def mark_billing_notice_read(
    notice_id: uuid.UUID,
    session: SessionDep,
    current_user: CurrentUser,
) -> BillingNoticePublic:
    return mark_billing_notice_status(
        session=session,
        user_id=current_user.id,
        notice_id=notice_id,
        status_value="read",
    )


@router.post(
    "/notices/{notice_id}/dismiss",
    response_model=BillingNoticePublic,
    dependencies=[Depends(rate_limit(POLICIES.private_basic))],
)
def dismiss_billing_notice(
    notice_id: uuid.UUID,
    session: SessionDep,
    current_user: CurrentUser,
) -> BillingNoticePublic:
    return mark_billing_notice_status(
        session=session,
        user_id=current_user.id,
        notice_id=notice_id,
        status_value="dismissed",
    )


@router.post("/webhooks/stripe", response_model=BillingWebhookReceipt)
async def stripe_webhook(
    request: Request,
    session: SessionDep,
    stripe_signature: Annotated[str, Header(alias="Stripe-Signature")],
) -> BillingWebhookReceipt:
    payload_raw = await request.body()
    verify_stripe_signature(
        payload=payload_raw,
        signature_header=stripe_signature,
    )
    payload = await request.json()
    user_id = await process_stripe_webhook(session=session, payload=payload)
    if user_id is not None:
        await publish_billing_event(
            session=session,
            user_id=user_id,
            event_name="account.subscription.updated",
        )
    return BillingWebhookReceipt(received=True)


__all__ = ["router"]
