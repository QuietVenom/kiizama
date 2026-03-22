from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any

from kiizama_scrape_core.ig_scraper.classes import CredentialCandidate
from kiizama_scrape_core.ig_scraper.ports import (
    InstagramCredentialsStore,
    InstagramProfileAnalysisService,
    InstagramScrapePersistence,
)
from kiizama_scrape_core.ig_scraper.schemas import InstagramBatchScrapeResponse
from kiizama_scrape_core.ig_scraper.types.session_validator import (
    configure_credentials_store_resolver,
)
from pydantic import AnyUrl, BaseModel, TypeAdapter, ValidationError

from app.core.ig_credentials_crypto import decrypt_ig_password
from app.core.mongodb import get_mongo_kiizama_ig
from app.crud.ig_credentials import list_ig_credentials, update_ig_credential_session
from app.crud.metrics import create_metrics, replace_metrics
from app.crud.posts import create_post, replace_post
from app.crud.profile import (
    create_profile,
    get_profile_by_username,
    get_profiles_by_usernames,
    update_profile,
)
from app.crud.profile_snapshots import (
    create_profile_snapshot,
    get_profile_snapshot_by_profile_id,
    replace_profile_snapshot,
)
from app.crud.reels import create_reel, replace_reel
from app.features.openai.classes import (
    IG_OPENAI_REQUEST,
    InstagramProfileAnalysisInput,
    deserialize_profile_analysis_response,
    serialize_profile_analysis_payload,
)
from app.features.openai.classes.openai_system_prompts import (
    SYSTEM_PROMPT_IG_OPENAI_REQUEST,
)
from app.features.openai.service import OpenAIService
from app.schemas import (
    Metrics,
    Post,
    PostItem,
    PostMetrics,
    Profile,
    ProfileSnapshot,
    Reel,
    ReelItem,
    ReelMetrics,
    UpdateProfile,
)

_URL_ADAPTER = TypeAdapter(AnyUrl)


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


def _require_document(doc: dict[str, Any] | None, *, message: str) -> dict[str, Any]:
    if doc is None:
        raise ValueError(message)
    return doc


class BackendInstagramCredentialsStore(InstagramCredentialsStore):
    def __init__(
        self,
        collection_provider: Callable[[], Any],
        decrypt_password: Callable[[str], str] = decrypt_ig_password,
    ) -> None:
        self._collection_provider = collection_provider
        self._decrypt_password = decrypt_password

    async def list_credentials(self, *, limit: int) -> list[CredentialCandidate]:
        docs = await list_ig_credentials(
            self._collection_provider(), skip=0, limit=limit
        )
        credentials: list[CredentialCandidate] = []

        for doc in docs:
            credential_id = doc.get("_id")
            if credential_id is None:
                continue

            login_username = doc.get("login_username")
            if isinstance(login_username, str):
                login_username = login_username.strip()
            else:
                login_username = None

            encrypted_password = doc.get("password")
            if not isinstance(encrypted_password, str):
                encrypted_password = None

            session = doc.get("session")
            if isinstance(session, str):
                try:
                    session = json.loads(session)
                except json.JSONDecodeError:
                    session = None
            if not isinstance(session, dict) or not session:
                session = None

            credentials.append(
                CredentialCandidate(
                    id=str(credential_id),
                    login_username=login_username,
                    encrypted_password=encrypted_password,
                    session=session,
                )
            )

        return credentials

    def decrypt_password(self, encrypted_password: str) -> str:
        return self._decrypt_password(encrypted_password)

    async def persist_session(self, credential_id: str, state: dict[str, Any]) -> bool:
        updated = await update_ig_credential_session(
            self._collection_provider(),
            credential_id,
            state,
        )
        return updated is not None


class BackendInstagramProfileAnalysisService(InstagramProfileAnalysisService):
    def __init__(
        self,
        openai_service_factory: Callable[[], OpenAIService] = OpenAIService,
    ) -> None:
        self._openai_service_factory = openai_service_factory
        self._openai_service: OpenAIService | None = None
        self._logger = logging.getLogger(__name__)

    def _get_openai_service(self) -> OpenAIService:
        if self._openai_service is None:
            self._openai_service = self._openai_service_factory()
        return self._openai_service

    async def enrich_scrape_response(
        self,
        response: InstagramBatchScrapeResponse,
    ) -> InstagramBatchScrapeResponse:
        if response.error:
            self._logger.info(
                "Skipping AI analysis because batch response has error: %s",
                response.error,
            )
            return response

        if not response.results:
            return response

        openai_service = self._get_openai_service()
        usernames: list[str] = []
        inputs: list[InstagramProfileAnalysisInput] = []

        for username, profile_result in response.results.items():
            if not profile_result.success:
                self._logger.debug(
                    "Skipping AI analysis for %s because scrape failed",
                    username,
                )
                continue

            inputs.append(
                InstagramProfileAnalysisInput(
                    username=profile_result.user.username or username,
                    biography=profile_result.user.biography,
                    follower_count=profile_result.user.follower_count,
                    posts=profile_result.posts,
                )
            )
            usernames.append(username)

        if not inputs:
            return response

        try:
            serialized = serialize_profile_analysis_payload(inputs)
            req_kwargs = IG_OPENAI_REQUEST.to_function_kwargs()
            req_kwargs["prompt"] = json.dumps(serialized, ensure_ascii=False)
            req_kwargs["system_prompt"] = SYSTEM_PROMPT_IG_OPENAI_REQUEST

            text = await asyncio.to_thread(
                openai_service.execute,
                "create_response",
                function_kwargs=req_kwargs,
            )

            raw = json.loads(text)
            parsed = deserialize_profile_analysis_response(raw)
            ai_results = parsed.results

            if len(ai_results) != len(inputs):
                self._logger.warning(
                    "AI results count mismatch: expected %s got %s",
                    len(inputs),
                    len(ai_results),
                )

            for idx, username in enumerate(usernames):
                profile_result = response.results[username]
                if idx < len(ai_results):
                    profile_result.ai_categories = ai_results[idx].categories
                    profile_result.ai_roles = ai_results[idx].roles
                else:
                    profile_result.ai_error = "AI response missing for this profile"

        except Exception as exc:  # pragma: no cover - resilience for AI call
            self._logger.warning("AI analysis failed for batch: %s", exc)
            for username in usernames:
                response.results[username].ai_error = str(exc)

        return response


class BackendInstagramScrapePersistence(InstagramScrapePersistence):
    def __init__(
        self,
        *,
        profiles_collection: Any,
        posts_collection: Any,
        reels_collection: Any,
        metrics_collection: Any,
        snapshots_collection: Any,
    ) -> None:
        self.profiles_collection = profiles_collection
        self.posts_collection = posts_collection
        self.reels_collection = reels_collection
        self.metrics_collection = metrics_collection
        self.snapshots_collection = snapshots_collection

    async def get_profiles_by_usernames(
        self,
        usernames: list[str],
    ) -> list[dict[str, Any]]:
        return await get_profiles_by_usernames(self.profiles_collection, usernames)

    async def persist_scrape_results(
        self,
        response: InstagramBatchScrapeResponse,
    ) -> InstagramBatchScrapeResponse:
        if response.error or not response.results:
            return response

        errors: list[str] = []
        now = datetime.now(timezone.utc)

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
                profile_payload = {
                    "ig_id": ig_id,
                    "username": username_value,
                    "full_name": _get_field_value(user, "full_name") or "",
                    "biography": _get_field_value(user, "biography") or "",
                    "is_private": bool(_get_field_value(user, "is_private", False)),
                    "is_verified": bool(_get_field_value(user, "is_verified", False)),
                    "profile_pic_url": profile_pic_url,
                    "external_url": external_url,
                    "updated_date": now,
                    "follower_count": int(
                        _get_field_value(user, "follower_count", 0) or 0
                    ),
                    "following_count": int(
                        _get_field_value(user, "following_count", 0) or 0
                    ),
                    "media_count": int(_get_field_value(user, "media_count", 0) or 0),
                    "bio_links": bio_links,
                    "ai_categories": profile_result.ai_categories or [],
                    "ai_roles": profile_result.ai_roles or [],
                }

                existing_profile = await get_profile_by_username(
                    self.profiles_collection,
                    username_value,
                )
                if not existing_profile:
                    existing_profile = await self.profiles_collection.find_one(
                        {"ig_id": ig_id}
                    )

                if existing_profile:
                    profile_doc = await update_profile(
                        self.profiles_collection,
                        str(existing_profile["_id"]),
                        UpdateProfile(**profile_payload),
                    )
                else:
                    profile_doc = await create_profile(
                        self.profiles_collection,
                        Profile(**profile_payload),
                    )

                profile_doc = _require_document(
                    profile_doc,
                    message=f"Failed to persist profile for username '{username_value}'",
                )
                profile_id = str(profile_doc["_id"])

                posts_payload: list[PostItem] = []
                for post in _coerce_list(profile_result.posts):
                    code = _get_field_value(post, "code")
                    if not code:
                        continue
                    posts_payload.append(
                        PostItem(
                            code=code,
                            caption_text=_get_field_value(post, "caption_text"),
                            is_paid_partnership=_get_field_value(
                                post, "is_paid_partnership"
                            ),
                            coauthor_producers=_get_field_value(
                                post,
                                "coauthor_producers",
                                [],
                            )
                            or [],
                            comment_count=_get_field_value(post, "comment_count"),
                            like_count=_get_field_value(post, "like_count"),
                            usertags=_get_field_value(post, "usertags", []) or [],
                            media_type=_get_field_value(post, "media_type"),
                            product_type=_get_field_value(post, "product_type"),
                        )
                    )

                reels_payload: list[ReelItem] = []
                for reel in _coerce_list(profile_result.reels):
                    code = _get_field_value(reel, "code")
                    if not code:
                        continue
                    reels_payload.append(
                        ReelItem(
                            code=code,
                            play_count=_get_field_value(reel, "play_count"),
                            comment_count=_get_field_value(reel, "comment_count"),
                            like_count=_get_field_value(reel, "like_count"),
                            media_type=_get_field_value(reel, "media_type"),
                            product_type=_get_field_value(reel, "product_type"),
                        )
                    )

                snapshot_doc = await get_profile_snapshot_by_profile_id(
                    self.snapshots_collection,
                    profile_id,
                )

                post_id = None
                if snapshot_doc:
                    post_ids = snapshot_doc.get("post_ids") or []
                    if post_ids:
                        post_id = str(post_ids[0])

                if post_id:
                    post_doc = await replace_post(
                        self.posts_collection,
                        post_id,
                        Post(
                            profile_id=profile_id,
                            posts=posts_payload,
                            updated_at=now,
                        ),
                    )
                else:
                    post_doc = await create_post(
                        self.posts_collection,
                        Post(
                            profile_id=profile_id,
                            posts=posts_payload,
                            updated_at=now,
                        ),
                    )
                post_doc = _require_document(
                    post_doc,
                    message=(
                        "Failed to persist posts document for "
                        f"username '{username_value}'"
                    ),
                )

                reel_id = None
                if snapshot_doc:
                    reel_ids = snapshot_doc.get("reel_ids") or []
                    if reel_ids:
                        reel_id = str(reel_ids[0])

                if reel_id:
                    reel_doc = await replace_reel(
                        self.reels_collection,
                        reel_id,
                        Reel(
                            profile_id=profile_id,
                            reels=reels_payload,
                            updated_at=now,
                        ),
                    )
                else:
                    reel_doc = await create_reel(
                        self.reels_collection,
                        Reel(
                            profile_id=profile_id,
                            reels=reels_payload,
                            updated_at=now,
                        ),
                    )
                reel_doc = _require_document(
                    reel_doc,
                    message=(
                        "Failed to persist reels document for "
                        f"username '{username_value}'"
                    ),
                )

                metrics_source = profile_result.metrics
                post_metrics = PostMetrics.model_validate(
                    _coerce_dict(_get_field_value(metrics_source, "post_metrics"))
                )
                reel_metrics = ReelMetrics.model_validate(
                    _coerce_dict(_get_field_value(metrics_source, "reel_metrics"))
                )
                overall_engagement_rate = float(
                    _get_field_value(metrics_source, "overall_engagement_rate", 0.0)
                    or 0.0
                )

                metrics_id = None
                if snapshot_doc and snapshot_doc.get("metrics_id"):
                    metrics_id = str(snapshot_doc["metrics_id"])

                if metrics_id:
                    metrics_doc = await replace_metrics(
                        self.metrics_collection,
                        metrics_id,
                        Metrics(
                            post_metrics=post_metrics,
                            reel_metrics=reel_metrics,
                            overall_engagement_rate=overall_engagement_rate,
                        ),
                    )
                else:
                    metrics_doc = await create_metrics(
                        self.metrics_collection,
                        Metrics(
                            post_metrics=post_metrics,
                            reel_metrics=reel_metrics,
                            overall_engagement_rate=overall_engagement_rate,
                        ),
                    )
                metrics_doc = _require_document(
                    metrics_doc,
                    message=(
                        "Failed to persist metrics document for "
                        f"username '{username_value}'"
                    ),
                )

                snapshot_payload = ProfileSnapshot(
                    profile_id=profile_id,
                    post_ids=[str(post_doc["_id"])],
                    reel_ids=[str(reel_doc["_id"])],
                    metrics_id=str(metrics_doc["_id"]),
                    scraped_at=now,
                )

                if snapshot_doc:
                    await replace_profile_snapshot(
                        self.snapshots_collection,
                        str(snapshot_doc["_id"]),
                        snapshot_payload,
                    )
                else:
                    await create_profile_snapshot(
                        self.snapshots_collection,
                        snapshot_payload,
                    )

            except Exception as exc:
                errors.append(f"{username}: {exc}")

        if errors:
            response.error = "Persistence errors: " + "; ".join(errors)

        return response


def configure_backend_instagram_scraper_runtime() -> None:
    configure_credentials_store_resolver(
        lambda: BackendInstagramCredentialsStore(
            lambda: get_mongo_kiizama_ig().get_collection("ig_credentials")
        )
    )


__all__ = [
    "BackendInstagramCredentialsStore",
    "BackendInstagramProfileAnalysisService",
    "BackendInstagramScrapePersistence",
    "configure_backend_instagram_scraper_runtime",
]
