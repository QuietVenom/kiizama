from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlmodel import Session, select

from app.models import IgScrapeJob, UserLegalAcceptance


@dataclass(slots=True)
class UserRelatedCleanupContext:
    legal_acceptances: list[UserLegalAcceptance]
    ig_scrape_jobs: list[IgScrapeJob]


def build_user_related_cleanup_context(
    *,
    session: Session,
    user_id: uuid.UUID,
) -> UserRelatedCleanupContext:
    return UserRelatedCleanupContext(
        legal_acceptances=list(
            session.exec(
                select(UserLegalAcceptance).where(
                    UserLegalAcceptance.user_id == user_id
                )
            ).all()
        ),
        ig_scrape_jobs=list(
            session.exec(
                select(IgScrapeJob).where(IgScrapeJob.owner_user_id == user_id)
            ).all()
        ),
    )


def delete_user_related_cleanup_context(
    *,
    session: Session,
    context: UserRelatedCleanupContext,
) -> None:
    for legal_acceptance in context.legal_acceptances:
        session.delete(legal_acceptance)

    for ig_scrape_job in context.ig_scrape_jobs:
        session.delete(ig_scrape_job)

    if context.legal_acceptances or context.ig_scrape_jobs:
        session.flush()


__all__ = [
    "UserRelatedCleanupContext",
    "build_user_related_cleanup_context",
    "delete_user_related_cleanup_context",
]
