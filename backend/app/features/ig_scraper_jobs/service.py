from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone
from typing import Annotated, Any, Protocol

from fastapi import Depends
from kiizama_scrape_core.ig_scraper.jobs import (
    JOB_STATUS_VALUES,
    build_instagram_job_queue_spec,
    build_job_projection_document,
    build_job_references,
    default_job_expires_at,
    serialize_job_document,
)
from kiizama_scrape_core.ig_scraper.schemas import (
    InstagramScrapeJobCreateRequest,
    InstagramScrapeJobStatusResponse,
    InstagramScrapeJobTerminalEventPayload,
    InstagramScrapeJobTerminalizationRequest,
    InstagramScrapeJobTerminalizationResponse,
)
from kiizama_scrape_core.job_control.keys import build_dedupe_key
from kiizama_scrape_core.job_control.schemas import (
    JobStatus,
    JobTransientState,
    QueuedJobMessage,
    TerminalizationDecision,
)
from kiizama_scrape_core.user_events.schemas import UserEventEnvelope

from app.api.deps import SessionDep
from app.core.config import settings
from app.core.ids import generate_uuid7
from app.features.ig_scraper_jobs.repository import SqlJobProjectionRepository
from app.features.job_control.repository import (
    JobControlRepository,
    JobControlUnavailableError,
)
from app.features.job_control.schemas import JobQueueSpec
from app.features.user_events.repository import (
    UserEventsRepository,
)

TERMINAL_JOB_STATUSES = {"done", "failed"}
TERMINAL_NOTIFICATION_KIND = "terminal"
TERMINAL_EVENT_SOURCE = "ig-scraper"
TERMINAL_EVENT_TOPIC = "jobs"


class JobProjectionCollection(Protocol):
    async def insert_one(self, document: dict[str, Any], /) -> Any: ...

    async def delete_one(self, filter: dict[str, Any], /) -> Any: ...

    async def find_one(
        self,
        filter: dict[str, Any],
        projection: dict[str, int] | None = None,
        /,
    ) -> dict[str, Any] | None: ...

    async def update_one(
        self,
        filter: dict[str, Any],
        update: dict[str, Any],
        /,
    ) -> Any: ...


class JobControlPort(Protocol):
    spec: JobQueueSpec

    async def enqueue_job(self, message: QueuedJobMessage) -> None: ...

    async def read_state(self, job_id: str) -> JobTransientState | None: ...

    async def claim_terminal_state(
        self,
        job_id: str,
        *,
        status: JobStatus,
        attempt: int,
        worker_id: str,
        completed_at: datetime,
        notification_id: str,
    ) -> TerminalizationDecision: ...

    async def complete_terminal_state(
        self,
        job_id: str,
        *,
        terminal_event_id: str,
    ) -> JobTransientState | None: ...


class UserEventsPort(Protocol):
    async def publish_event(
        self,
        *,
        user_id: str,
        event_name: str,
        envelope: UserEventEnvelope,
        dedupe_key: str | None = None,
        dedupe_ttl_seconds: int | None = None,
    ) -> tuple[str, bool]: ...


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def get_instagram_job_queue_spec() -> JobQueueSpec:
    return build_instagram_job_queue_spec(
        state_ttl_seconds=settings.JOB_CONTROL_TERMINAL_STATE_TTL_SECONDS,
        queue_maxlen=settings.JOB_CONTROL_QUEUE_MAXLEN,
    )


def get_instagram_job_projection_repository(
    session: SessionDep,
) -> SqlJobProjectionRepository:
    return SqlJobProjectionRepository(session=session)


def get_instagram_job_control_repository() -> JobControlRepository:
    return JobControlRepository(spec=get_instagram_job_queue_spec())


def get_instagram_user_events_repository() -> UserEventsRepository:
    return UserEventsRepository()


class InstagramJobService:
    def __init__(
        self,
        *,
        jobs_collection: JobProjectionCollection,
        job_control_repository: JobControlPort,
        user_events_repository: UserEventsPort,
        clock: Callable[[], datetime] = utcnow,
    ) -> None:
        self._jobs_collection = jobs_collection
        self._job_control_repository = job_control_repository
        self._user_events_repository = user_events_repository
        self._job_spec = job_control_repository.spec
        self._clock = clock

    async def create_job(
        self,
        *,
        payload: InstagramScrapeJobCreateRequest,
        owner_user_id: str,
    ) -> str:
        now = self._clock()
        job_id = str(generate_uuid7())
        expires_at = default_job_expires_at(reference_time=now)
        projection = build_job_projection_document(
            job_id=job_id,
            owner_user_id=owner_user_id,
            payload=payload.model_dump(mode="json"),
            created_at=now,
            expires_at=expires_at,
        )

        await self._jobs_collection.insert_one(projection)

        try:
            await self._job_control_repository.enqueue_job(
                QueuedJobMessage(
                    job_id=job_id,
                    owner_user_id=owner_user_id,
                    created_at=now,
                    expires_at=expires_at,
                    payload=payload.model_dump(mode="json"),
                )
            )
        except JobControlUnavailableError:
            await self._jobs_collection.delete_one({"_id": job_id})
            raise

        return job_id

    async def get_job(
        self,
        *,
        job_id: str,
    ) -> InstagramScrapeJobStatusResponse | None:
        doc = await self._jobs_collection.find_one({"_id": job_id}, {"payload": 0})
        if doc is None:
            return None

        try:
            state = await self._job_control_repository.read_state(job_id)
        except JobControlUnavailableError:
            if str(doc.get("status")) in TERMINAL_JOB_STATUSES:
                return serialize_job_document(doc)
            raise

        if state is None:
            return self._serialize_projection_without_live_state(doc)

        return serialize_job_document(self._merge_projection_with_state(doc, state))

    async def complete_job(
        self,
        *,
        job_id: str,
        payload: InstagramScrapeJobTerminalizationRequest,
    ) -> InstagramScrapeJobTerminalizationResponse | None:
        doc = await self._jobs_collection.find_one({"_id": job_id})
        if doc is None:
            return None

        owner_user_id = str(doc.get("ownerUserId") or "").strip()
        if not owner_user_id:
            raise RuntimeError(f"Job {job_id} is missing ownerUserId.")

        notification_id = self._build_notification_id(job_id)
        decision = await self._job_control_repository.claim_terminal_state(
            job_id,
            status=payload.status,
            attempt=payload.attempt,
            worker_id=payload.worker_id,
            completed_at=payload.completed_at,
            notification_id=notification_id,
        )

        response = InstagramScrapeJobTerminalizationResponse(
            job_id=job_id,
            decision=decision.decision,
            status=decision.status,
            notification_id=decision.notification_id or notification_id,
            terminal_event_id=decision.terminal_event_id,
        )
        if decision.decision == "conflict":
            return response
        if decision.decision == "duplicate":
            return response

        references = build_job_references(payload.summary)
        await self._jobs_collection.update_one(
            {"_id": job_id},
            {
                "$set": {
                    "status": payload.status,
                    "updatedAt": payload.completed_at,
                    "completedAt": payload.completed_at,
                    "summary": payload.summary.model_dump(mode="json"),
                    "references": references.model_dump(mode="json"),
                    "error": payload.error,
                    "notificationId": notification_id,
                }
            },
        )

        event_payload = self._build_terminal_event_payload(
            job_id=job_id,
            doc=doc,
            payload=payload,
            notification_id=notification_id,
        )
        event_id, _published = await self._user_events_repository.publish_event(
            user_id=owner_user_id,
            event_name=self._build_event_name(payload.status),
            envelope=UserEventEnvelope(
                topic=TERMINAL_EVENT_TOPIC,
                source=TERMINAL_EVENT_SOURCE,
                kind=TERMINAL_NOTIFICATION_KIND,
                notification_id=notification_id,
                payload=event_payload.model_dump(mode="json"),
            ),
            dedupe_key=build_dedupe_key(
                self._job_spec,
                job_id,
                TERMINAL_NOTIFICATION_KIND,
            ),
            dedupe_ttl_seconds=self._job_spec.state_ttl_seconds,
        )
        await self._job_control_repository.complete_terminal_state(
            job_id,
            terminal_event_id=event_id,
        )

        return response.model_copy(update={"terminal_event_id": event_id})

    @staticmethod
    def _build_notification_id(job_id: str) -> str:
        return f"job:{job_id}:{TERMINAL_NOTIFICATION_KIND}"

    @staticmethod
    def _build_event_name(status: str) -> str:
        if status == "done":
            return "ig-scrape.job.completed"
        return "ig-scrape.job.failed"

    @staticmethod
    def _merge_projection_with_state(
        doc: dict[str, Any],
        state: JobTransientState,
    ) -> dict[str, Any]:
        merged = dict(doc)
        if state.status in JOB_STATUS_VALUES:
            merged["status"] = state.status
        if state.updated_at is not None:
            merged["updatedAt"] = state.updated_at
        merged["attempts"] = state.attempts
        merged["worker_id"] = state.worker_id
        merged["leased_until"] = state.leased_until
        merged["heartbeat_at"] = state.heartbeat_at
        return merged

    @staticmethod
    def _serialize_projection_without_live_state(
        doc: dict[str, Any],
    ) -> InstagramScrapeJobStatusResponse:
        status = str(doc.get("status") or "")
        if status == "queued" or status in TERMINAL_JOB_STATUSES:
            return serialize_job_document(doc)
        raise RuntimeError(
            "Unexpected transient job projection without live Redis state. "
            f"job_id={doc.get('_id')} status={status!r}"
        )

    @staticmethod
    def _build_terminal_event_payload(
        *,
        job_id: str,
        doc: dict[str, Any],
        payload: InstagramScrapeJobTerminalizationRequest,
        notification_id: str,
    ) -> InstagramScrapeJobTerminalEventPayload:
        requested_usernames = [item.username for item in payload.summary.usernames]
        successful_usernames = [
            item.username
            for item in payload.summary.usernames
            if item.status == "success"
        ]
        skipped_usernames = [
            item.username
            for item in payload.summary.usernames
            if item.status == "skipped"
        ]
        failed_usernames = [
            item.username
            for item in payload.summary.usernames
            if item.status == "failed"
        ]
        not_found_usernames = [
            item.username
            for item in payload.summary.usernames
            if item.status == "not_found"
        ]
        ready_usernames = [
            item.username
            for item in payload.summary.usernames
            if item.status in {"success", "skipped"}
        ]

        return InstagramScrapeJobTerminalEventPayload(
            notification_id=notification_id,
            job_id=job_id,
            status=payload.status,
            created_at=doc["createdAt"],
            completed_at=payload.completed_at,
            requested_usernames=requested_usernames,
            ready_usernames=ready_usernames,
            successful_usernames=successful_usernames,
            skipped_usernames=skipped_usernames,
            failed_usernames=failed_usernames,
            not_found_usernames=not_found_usernames,
            counters=payload.summary.counters,
            error=payload.error,
        )


def get_instagram_job_service(
    jobs_collection: Annotated[
        JobProjectionCollection,
        Depends(get_instagram_job_projection_repository),
    ],
) -> InstagramJobService:
    return InstagramJobService(
        jobs_collection=jobs_collection,
        job_control_repository=get_instagram_job_control_repository(),
        user_events_repository=get_instagram_user_events_repository(),
    )


InstagramJobServiceDep = Annotated[
    InstagramJobService,
    Depends(get_instagram_job_service),
]


__all__ = [
    "InstagramJobService",
    "InstagramJobServiceDep",
    "TERMINAL_JOB_STATUSES",
    "get_instagram_job_control_repository",
    "get_instagram_job_projection_repository",
    "get_instagram_job_queue_spec",
    "get_instagram_job_service",
    "get_instagram_user_events_repository",
]
