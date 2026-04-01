from __future__ import annotations

import uuid
from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any, cast

from pydantic import AnyUrl, BaseModel, TypeAdapter, ValidationError
from sqlmodel import Session, select

from kiizama_scrape_core.crypto import (
    decrypt_ig_password,
    decrypt_ig_session,
    encrypt_ig_session,
)

from .classes import CredentialCandidate
from .ports import InstagramCredentialsStore, InstagramScrapePersistence
from .schemas import InstagramBatchScrapeResponse
from .service import NOT_FOUND_ERROR
from .sqlmodels import (
    IgCredential,
    IgMetrics,
    IgPostsDocument,
    IgProfile,
    IgProfileSnapshot,
    IgReelsDocument,
    IgScrapeJob,
)

_URL_ADAPTER = TypeAdapter(AnyUrl)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _get_field_value(item: Any, key: str, default: Any = None) -> Any:
    if isinstance(item, dict):
        return item.get(key, default)
    return getattr(item, key, default)


def _coerce_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, BaseModel):
        return value.model_dump()
    return {}


def _coerce_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    return []


def _sanitize_optional_url(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    candidate = value.strip()
    if not candidate:
        return None
    try:
        parsed = _URL_ADAPTER.validate_python(candidate)
    except ValidationError:
        return None
    return str(parsed)


def _sanitize_bio_links(value: Any) -> list[dict[str, Any]]:
    sanitized: list[dict[str, Any]] = []
    for item in _coerce_list(value):
        if not isinstance(item, dict):
            continue
        url = _sanitize_optional_url(item.get("url"))
        if not url:
            continue
        title_raw = item.get("title")
        title = title_raw.strip() if isinstance(title_raw, str) else ""
        sanitized.append({"title": title, "url": url})
    return sanitized


def _parse_uuid(raw_value: str) -> uuid.UUID:
    return uuid.UUID(raw_value)


def _serialize_credential(record: IgCredential) -> dict[str, Any]:
    try:
        session = decrypt_ig_session(record.session_encrypted)
    except ValueError:
        session = None
    return {
        "_id": str(record.id),
        "login_username": record.login_username,
        "password": record.password_encrypted,
        "session": session,
    }


def _serialize_profile(record: IgProfile) -> dict[str, Any]:
    return {
        "_id": str(record.id),
        "ig_id": record.ig_id,
        "username": record.username,
        "full_name": record.full_name or "",
        "biography": record.biography or "",
        "is_private": record.is_private,
        "is_verified": record.is_verified,
        "profile_pic_url": record.profile_pic_url,
        "profile_pic_src": None,
        "external_url": record.external_url,
        "updated_date": record.updated_at,
        "follower_count": record.follower_count,
        "following_count": record.following_count,
        "media_count": record.media_count,
        "bio_links": record.bio_links,
        "ai_categories": record.ai_categories,
        "ai_roles": record.ai_roles,
    }


class SqlInstagramCredentialsStore(InstagramCredentialsStore):
    def __init__(
        self,
        session_provider: Callable[[], Session],
        decrypt_password: Callable[[str], str] = decrypt_ig_password,
    ) -> None:
        self._session_provider = session_provider
        self._decrypt_password = decrypt_password

    async def list_credentials(self, *, limit: int) -> list[CredentialCandidate]:
        created_at = cast(Any, IgCredential.created_at)
        with self._session_provider() as session:
            records = session.exec(
                select(IgCredential).order_by(created_at).limit(limit)
            ).all()

        credentials: list[CredentialCandidate] = []
        for record in records:
            doc = _serialize_credential(record)
            credentials.append(
                CredentialCandidate(
                    id=str(doc["_id"]),
                    login_username=doc.get("login_username"),
                    encrypted_password=doc.get("password"),
                    session=doc.get("session"),
                )
            )
        return credentials

    def decrypt_password(self, encrypted_password: str) -> str:
        return self._decrypt_password(encrypted_password)

    async def persist_session(self, credential_id: str, state: dict[str, Any]) -> bool:
        parsed_id = _parse_uuid(credential_id)
        with self._session_provider() as session:
            record = session.get(IgCredential, parsed_id)
            if record is None:
                return False
            record.session_encrypted = encrypt_ig_session(state)
            record.updated_at = _utcnow()
            session.add(record)
            session.commit()
        return True


class SqlInstagramJobProjectionRepository:
    def __init__(self, *, session: Session) -> None:
        self._session = session

    @staticmethod
    def _parse_job_id(raw_job_id: Any) -> uuid.UUID | None:
        if not isinstance(raw_job_id, str):
            return None
        try:
            return uuid.UUID(raw_job_id)
        except ValueError:
            return None

    @staticmethod
    def _parse_owner_user_id(raw_owner_user_id: Any) -> uuid.UUID:
        if not isinstance(raw_owner_user_id, str):
            raise ValueError("Job projection is missing ownerUserId.")
        return uuid.UUID(raw_owner_user_id)

    @staticmethod
    def _serialize_job(record: IgScrapeJob) -> dict[str, Any]:
        return {
            "_id": str(record.id),
            "ownerUserId": str(record.owner_user_id),
            "executionMode": record.execution_mode,
            "status": record.status,
            "createdAt": record.created_at,
            "updatedAt": record.updated_at,
            "completedAt": record.completed_at,
            "expiresAt": record.expires_at,
            "payload": record.payload,
            "summary": record.summary,
            "references": record.references,
            "error": record.error_message,
            "notificationId": record.notification_id,
            "attempts": record.attempts,
            "worker_id": record.worker_id,
            "leased_until": record.leased_until,
            "heartbeat_at": record.heartbeat_at,
        }

    @staticmethod
    def _apply_projection(
        document: dict[str, Any],
        projection: dict[str, int] | None,
    ) -> dict[str, Any]:
        if not projection:
            return document
        projected = dict(document)
        for key, include in projection.items():
            if include == 0:
                projected.pop(key, None)
        return projected

    async def insert_one(self, document: dict[str, Any], /) -> None:
        record = IgScrapeJob(
            id=uuid.UUID(str(document["_id"])),
            owner_user_id=self._parse_owner_user_id(document.get("ownerUserId")),
            execution_mode=str(document.get("executionMode") or "worker"),
            status=str(document.get("status") or "queued"),
            attempts=int(document.get("attempts", 0) or 0),
            worker_id=document.get("worker_id"),
            leased_until=document.get("leased_until"),
            heartbeat_at=document.get("heartbeat_at"),
            completed_at=document.get("completedAt"),
            expires_at=document["expiresAt"],
            payload=document.get("payload") or {},
            summary=document.get("summary"),
            references=document.get("references"),
            error_message=document.get("error"),
            notification_id=document.get("notificationId"),
            created_at=document["createdAt"],
            updated_at=document["updatedAt"],
        )
        self._session.add(record)
        self._session.commit()

    async def delete_one(self, filter: dict[str, Any], /) -> None:
        job_id = self._parse_job_id(filter.get("_id"))
        if job_id is None:
            return
        record = self._session.get(IgScrapeJob, job_id)
        if record is None:
            return
        self._session.delete(record)
        self._session.commit()

    async def find_one(
        self,
        filter: dict[str, Any],
        projection: dict[str, int] | None = None,
        /,
    ) -> dict[str, Any] | None:
        job_id = self._parse_job_id(filter.get("_id"))
        if job_id is None:
            return None
        record = self._session.get(IgScrapeJob, job_id)
        if record is None:
            return None
        raw_owner_user_id = filter.get("ownerUserId")
        if raw_owner_user_id is not None:
            try:
                owner_user_id = self._parse_owner_user_id(raw_owner_user_id)
            except (TypeError, ValueError):
                return None
            if record.owner_user_id != owner_user_id:
                return None
        return self._apply_projection(self._serialize_job(record), projection)

    async def update_one(
        self,
        filter: dict[str, Any],
        update: dict[str, Any],
        /,
    ) -> None:
        job_id = self._parse_job_id(filter.get("_id"))
        if job_id is None:
            return
        record = self._session.get(IgScrapeJob, job_id)
        if record is None:
            return

        updates = update.get("$set", {})
        if "executionMode" in updates and updates["executionMode"] is not None:
            record.execution_mode = str(updates["executionMode"])
        if "status" in updates and updates["status"] is not None:
            record.status = str(updates["status"])
        if "updatedAt" in updates:
            record.updated_at = updates["updatedAt"]
        if "completedAt" in updates:
            record.completed_at = updates["completedAt"]
            if record.status == "failed":
                record.failed_at = updates["completedAt"]
        if "summary" in updates:
            record.summary = updates["summary"]
        if "references" in updates:
            record.references = updates["references"]
        if "error" in updates:
            record.error_message = updates["error"]
        if "notificationId" in updates:
            record.notification_id = updates["notificationId"]
        if "attempts" in updates:
            record.attempts = int(updates["attempts"] or 0)
        if "worker_id" in updates:
            record.worker_id = updates["worker_id"]
        if "leased_until" in updates:
            record.leased_until = updates["leased_until"]
        if "heartbeat_at" in updates:
            record.heartbeat_at = updates["heartbeat_at"]

        self._session.add(record)
        self._session.commit()


class SqlInstagramScrapePersistence(InstagramScrapePersistence):
    def __init__(self, *, session: Session) -> None:
        self._session = session

    async def get_profiles_by_usernames(
        self,
        usernames: list[str],
    ) -> list[dict[str, Any]]:
        if not usernames:
            return []
        username_column = cast(Any, IgProfile.username)
        records = self._session.exec(
            select(IgProfile).where(username_column.in_(usernames))
        ).all()
        return [_serialize_profile(record) for record in records]

    def _get_profile_by_username(self, username: str) -> IgProfile | None:
        return self._session.exec(
            select(IgProfile).where(IgProfile.username == username)
        ).first()

    def _get_profile_by_ig_id(self, ig_id: str) -> IgProfile | None:
        return self._session.exec(
            select(IgProfile).where(IgProfile.ig_id == ig_id)
        ).first()

    def _get_latest_snapshot(self, profile_id: uuid.UUID) -> IgProfileSnapshot | None:
        scraped_at = cast(Any, IgProfileSnapshot.scraped_at)
        return self._session.exec(
            select(IgProfileSnapshot)
            .where(IgProfileSnapshot.profile_id == profile_id)
            .order_by(scraped_at.desc())
        ).first()

    async def persist_scrape_results(
        self,
        response: InstagramBatchScrapeResponse,
    ) -> InstagramBatchScrapeResponse:
        if response.error or not response.results:
            return response

        errors: list[str] = []
        now = datetime.now(timezone.utc)
        try:
            for username, profile_result in response.results.items():
                if not profile_result.success:
                    continue

                try:
                    user = profile_result.user
                    ig_id = _get_field_value(user, "id")
                    if not ig_id:
                        raise ValueError("Missing ig_id")

                    profile_pic_url = _get_field_value(user, "profile_pic_url")
                    if not profile_pic_url:
                        raise ValueError("Missing profile_pic_url")

                    username_value = _get_field_value(user, "username") or username
                    external_url = _sanitize_optional_url(
                        _get_field_value(user, "external_url")
                    )
                    bio_links = _sanitize_bio_links(
                        _get_field_value(user, "bio_links", []) or []
                    )

                    profile_record = self._get_profile_by_username(username_value)
                    if profile_record is None:
                        profile_record = self._get_profile_by_ig_id(ig_id)

                    if profile_record is None:
                        profile_record = IgProfile(
                            ig_id=ig_id,
                            username=username_value,
                            created_at=now,
                        )

                    profile_record.full_name = _get_field_value(user, "full_name") or ""
                    profile_record.biography = _get_field_value(user, "biography") or ""
                    profile_record.is_private = bool(
                        _get_field_value(user, "is_private", False)
                    )
                    profile_record.is_verified = bool(
                        _get_field_value(user, "is_verified", False)
                    )
                    profile_record.profile_pic_url = profile_pic_url
                    profile_record.external_url = external_url
                    profile_record.follower_count = int(
                        _get_field_value(user, "follower_count", 0) or 0
                    )
                    profile_record.following_count = int(
                        _get_field_value(user, "following_count", 0) or 0
                    )
                    profile_record.media_count = int(
                        _get_field_value(user, "media_count", 0) or 0
                    )
                    profile_record.bio_links = bio_links
                    profile_record.ai_categories = profile_result.ai_categories or []
                    profile_record.ai_roles = profile_result.ai_roles or []
                    profile_record.updated_at = now
                    self._session.add(profile_record)
                    self._session.flush()

                    posts_items: list[dict[str, Any]] = []
                    for post in _coerce_list(profile_result.posts):
                        code = _get_field_value(post, "code")
                        if not code:
                            continue
                        posts_items.append(
                            {
                                "code": code,
                                "caption_text": _get_field_value(post, "caption_text"),
                                "is_paid_partnership": _get_field_value(
                                    post, "is_paid_partnership"
                                ),
                                "coauthor_producers": _get_field_value(
                                    post, "coauthor_producers", []
                                )
                                or [],
                                "comment_count": _get_field_value(
                                    post, "comment_count"
                                ),
                                "like_count": _get_field_value(post, "like_count"),
                                "usertags": _get_field_value(post, "usertags", [])
                                or [],
                                "media_type": _get_field_value(post, "media_type"),
                                "product_type": _get_field_value(post, "product_type"),
                            }
                        )

                    reels_items: list[dict[str, Any]] = []
                    for reel in _coerce_list(profile_result.reels):
                        code = _get_field_value(reel, "code")
                        if not code:
                            continue
                        reels_items.append(
                            {
                                "code": code,
                                "play_count": _get_field_value(reel, "play_count"),
                                "comment_count": _get_field_value(
                                    reel, "comment_count"
                                ),
                                "like_count": _get_field_value(reel, "like_count"),
                                "media_type": _get_field_value(reel, "media_type"),
                                "product_type": _get_field_value(reel, "product_type"),
                            }
                        )

                    snapshot = self._get_latest_snapshot(profile_record.id)

                    posts_record = (
                        self._session.get(IgPostsDocument, snapshot.posts_document_id)
                        if snapshot and snapshot.posts_document_id
                        else None
                    )
                    if posts_record is None:
                        posts_record = IgPostsDocument(profile_id=profile_record.id)
                    posts_record.profile_id = profile_record.id
                    posts_record.items = posts_items
                    posts_record.updated_at = now
                    self._session.add(posts_record)
                    self._session.flush()

                    reels_record = (
                        self._session.get(IgReelsDocument, snapshot.reels_document_id)
                        if snapshot and snapshot.reels_document_id
                        else None
                    )
                    if reels_record is None:
                        reels_record = IgReelsDocument(profile_id=profile_record.id)
                    reels_record.profile_id = profile_record.id
                    reels_record.items = reels_items
                    reels_record.updated_at = now
                    self._session.add(reels_record)
                    self._session.flush()

                    metrics_source = profile_result.metrics
                    metrics_record = (
                        self._session.get(IgMetrics, snapshot.metrics_id)
                        if snapshot and snapshot.metrics_id
                        else None
                    )
                    if metrics_record is None:
                        metrics_record = IgMetrics()

                    post_metrics = _coerce_dict(
                        _get_field_value(metrics_source, "post_metrics")
                    )
                    reel_metrics = _coerce_dict(
                        _get_field_value(metrics_source, "reel_metrics")
                    )
                    metrics_record.total_posts = int(
                        post_metrics.get("total_posts", 0) or 0
                    )
                    metrics_record.total_likes = int(
                        post_metrics.get("total_likes", 0) or 0
                    )
                    metrics_record.total_comments = int(
                        post_metrics.get("total_comments", 0) or 0
                    )
                    metrics_record.avg_likes = float(
                        post_metrics.get("avg_likes", 0.0) or 0.0
                    )
                    metrics_record.avg_comments = float(
                        post_metrics.get("avg_comments", 0.0) or 0.0
                    )
                    metrics_record.avg_engagement_rate = float(
                        post_metrics.get("avg_engagement_rate", 0.0) or 0.0
                    )
                    metrics_record.hashtags_per_post = float(
                        post_metrics.get("hashtags_per_post", 0.0) or 0.0
                    )
                    metrics_record.mentions_per_post = float(
                        post_metrics.get("mentions_per_post", 0.0) or 0.0
                    )
                    metrics_record.total_reels = int(
                        reel_metrics.get("total_reels", 0) or 0
                    )
                    metrics_record.total_plays = int(
                        reel_metrics.get("total_plays", 0) or 0
                    )
                    metrics_record.avg_plays = float(
                        reel_metrics.get("avg_plays", 0.0) or 0.0
                    )
                    metrics_record.avg_reel_likes = float(
                        reel_metrics.get("avg_reel_likes", 0.0) or 0.0
                    )
                    metrics_record.avg_reel_comments = float(
                        reel_metrics.get("avg_reel_comments", 0.0) or 0.0
                    )
                    metrics_record.overall_post_engagement_rate = float(
                        _get_field_value(
                            metrics_source, "overall_post_engagement_rate", 0.0
                        )
                        or 0.0
                    )
                    metrics_record.reel_engagement_rate_on_plays = float(
                        _get_field_value(
                            metrics_source, "reel_engagement_rate_on_plays", 0.0
                        )
                        or 0.0
                    )
                    metrics_record.updated_at = now
                    self._session.add(metrics_record)
                    self._session.flush()

                    if snapshot is None:
                        snapshot = IgProfileSnapshot(
                            profile_id=profile_record.id, created_at=now
                        )
                    snapshot.profile_id = profile_record.id
                    snapshot.posts_document_id = posts_record.id
                    snapshot.reels_document_id = reels_record.id
                    snapshot.metrics_id = metrics_record.id
                    snapshot.scraped_at = now
                    snapshot.updated_at = now
                    self._session.add(snapshot)
                except Exception as exc:
                    profile_result.success = False
                    profile_result.error = str(exc)
                    errors.append(f"{username}: {exc}")

            self._session.commit()
        except Exception:
            self._session.rollback()
            raise

        if errors:
            response.error = "Persistence errors: " + "; ".join(errors)
            response.counters.requested = len(response.results)
            response.counters.successful = sum(
                1 for result in response.results.values() if result.success
            )
            response.counters.not_found = sum(
                1
                for result in response.results.values()
                if not result.success and result.error == NOT_FOUND_ERROR
            )
            response.counters.failed = (
                response.counters.requested
                - response.counters.successful
                - response.counters.not_found
            )
        return response


__all__ = [
    "SqlInstagramCredentialsStore",
    "SqlInstagramJobProjectionRepository",
    "SqlInstagramScrapePersistence",
]
