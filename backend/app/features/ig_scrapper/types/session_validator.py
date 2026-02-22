from __future__ import annotations

import json
import random
from collections.abc import Callable, Mapping
from typing import Any

from playwright.async_api import Page, StorageState
from playwright.async_api import TimeoutError as PlaywrightTimeoutError

from app.constants import DEFAULT_USER_AGENT
from app.core.ig_credentials_crypto import decrypt_ig_password
from app.crud.ig_credentials import (
    list_ig_credentials,
    update_ig_credential_session,
)

from ..classes import CredentialCandidate, SessionValidationResult
from .base import (
    BaseInstagramWorker,
    NetworkUsage,
    PlaywrightBrowserNotInstalledError,
)
from .login_flow import InstagramLoginFlow

StorageStateLike = StorageState | Mapping[str, Any]

MAX_LOGIN_ATTEMPTS = 3
MAX_CREDENTIALS_FETCH = 200
_credentials_collection_resolver: Callable[[], Any] | None = None


def configure_credentials_collection_resolver(
    resolver: Callable[[], Any] | None,
) -> None:
    global _credentials_collection_resolver
    _credentials_collection_resolver = resolver


class InstagramSessionValidator(BaseInstagramWorker):
    """Validate or refresh an Instagram session stored in MongoDB."""

    def __init__(
        self,
        *,
        login_username: str | None = None,
        password: str | None = None,
        headless: bool = True,
        user_agent: str = DEFAULT_USER_AGENT,
        locale: str = "en-US",
        proxy: str | None = None,
        timeout_ms: int = 30000,
        measure_network_bytes: bool = False,
        network_usage: NetworkUsage | None = None,
    ) -> None:
        super().__init__(
            headless=headless,
            user_agent=user_agent or DEFAULT_USER_AGENT,
            locale=locale,
            proxy=proxy,
            timeout_ms=timeout_ms,
            measure=False,
            measure_network_bytes=measure_network_bytes,
            network_usage=network_usage,
        )

        self.login_username = (login_username or "").strip()
        self.password = password or ""
        self._encrypted_password: str | None = None
        self.credential_id: str | None = None
        self.storage_state: dict[str, Any] | None = None
        self._requested_user_agent = user_agent or DEFAULT_USER_AGENT
        self._requested_locale = locale
        self._credentials_collection = None

        self._raw_state: dict[str, Any] = {}
        self.extra_headers: dict[str, str] = {}
        self._apply_storage_state(self._raw_state)

    # ------------------------------------------------------------------
    # Storage state helpers
    # ------------------------------------------------------------------
    @staticmethod
    def extract_session_info(
        raw_state: dict[str, Any],
    ) -> tuple[dict[str, str], str | None, str | None]:
        headers: dict[str, str] = {}
        user_agent: str | None = None
        locale: str | None = None

        sess_raw = raw_state.get("__session")
        if isinstance(sess_raw, dict):
            raw_headers = sess_raw.get("headers")
            if isinstance(raw_headers, dict):
                headers = {
                    str(k): str(v)
                    for k, v in raw_headers.items()
                    if isinstance(k, str) and isinstance(v, str)
                }

            ua = sess_raw.get("user_agent")
            if isinstance(ua, str) and ua:
                user_agent = ua

            loc = sess_raw.get("locale")
            if isinstance(loc, str) and loc:
                locale = loc

        return headers, user_agent, locale

    def _apply_storage_state(self, raw_state: StorageStateLike | None) -> None:
        state = dict(raw_state) if raw_state else {}
        self._raw_state = state
        self.storage_state = state if state else None
        self.user_agent = self._requested_user_agent or DEFAULT_USER_AGENT
        self.locale = self._requested_locale

        headers, session_user_agent, session_locale = self.extract_session_info(
            self._raw_state
        )
        self.extra_headers = {
            k: v
            for k, v in headers.items()
            if k.lower() not in {"cookie", "user-agent"}
        }
        if session_user_agent and self._requested_user_agent == DEFAULT_USER_AGENT:
            self.user_agent = session_user_agent
        if session_locale:
            self.locale = session_locale

    # ------------------------------------------------------------------
    # Overrides
    # ------------------------------------------------------------------
    def build_context_options(self) -> dict[str, Any]:
        options = super().build_context_options()
        if self._raw_state:
            options["storage_state"] = self._raw_state
        if self.extra_headers:
            options["extra_http_headers"] = self.extra_headers
        options["viewport"] = {"width": 1920, "height": 1080}
        return options

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    async def ensure_session(self) -> SessionValidationResult:
        """Ensure there is an authenticated session, logging in if needed."""
        credentials = await self._load_credentials()
        viable = [
            cred for cred in credentials if cred.has_session() or cred.has_login()
        ]

        if not viable:
            message = "No Instagram credentials available"
            self.logger.error(message)
            return SessionValidationResult(
                success=False,
                credential_id=None,
                storage_state=None,
                message=message,
                error=message,
            )

        random.shuffle(viable)
        max_attempts = min(MAX_LOGIN_ATTEMPTS, len(viable))
        failed_ids: list[str] = []

        for idx, credential in enumerate(viable[:max_attempts], start=1):
            self.logger.info(
                "Instagram credential attempt %s/%s using id=%s username=%s",
                idx,
                max_attempts,
                credential.id,
                credential.login_username or "unknown",
            )
            try:
                result = await self._ensure_session_for_credential(credential)
            except PlaywrightBrowserNotInstalledError as exc:
                message = str(exc)
                self.logger.error(message)
                return SessionValidationResult(
                    success=False,
                    credential_id=credential.id,
                    storage_state=None,
                    message=message,
                    error=message,
                )
            except Exception as exc:
                message = f"Unexpected Instagram session validation error: {exc}"
                self.logger.exception(
                    "Unexpected session validation error for credential id=%s",
                    credential.id,
                )
                result = SessionValidationResult(
                    success=False,
                    credential_id=credential.id,
                    storage_state=self.storage_state,
                    message=message,
                    error=message,
                )
            if result.success:
                self.logger.info(
                    "Instagram session ready for id=%s username=%s",
                    credential.id,
                    credential.login_username or "unknown",
                )
                return result

            failed_ids.append(credential.id)
            self.logger.warning(
                "Instagram credential attempt failed for id=%s username=%s: %s",
                credential.id,
                credential.login_username or "unknown",
                result.error or result.message,
            )

        if failed_ids:
            self.logger.error(
                "Instagram credential attempts failed after %s tries. Failed ids=%s",
                len(failed_ids),
                ", ".join(failed_ids),
            )

        message = "Instagram login failed for all attempted credentials"
        return SessionValidationResult(
            success=False,
            credential_id=None,
            storage_state=None,
            message=message,
            error=message,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    async def _ensure_session_for_credential(
        self, credential: CredentialCandidate
    ) -> SessionValidationResult:
        self._apply_credential(credential)

        async with self:
            if self.page is None:
                message = "Playwright page could not be initialized"
                return SessionValidationResult(
                    success=False,
                    credential_id=self.credential_id,
                    storage_state=self.storage_state,
                    message=message,
                    error=message,
                )

            page = self.page

            # Try existing session
            if credential.has_session():
                self.logger.info(
                    "Validating stored session for credential id=%s",
                    credential.id,
                )
                if await self._navigate_to_home(
                    page
                ) and await self._has_logged_in_markers(page):
                    self.logger.info(
                        "Stored session valid for credential id=%s",
                        credential.id,
                    )
                    persisted = await self._persist_storage_state()
                    return SessionValidationResult(
                        success=True,
                        credential_id=self.credential_id,
                        storage_state=persisted or self.storage_state,
                        message="Existing Instagram session is valid",
                    )

                self.logger.info(
                    "Stored session invalid for credential id=%s",
                    credential.id,
                )

            if not self._ensure_login_credentials(credential):
                message = "Missing Instagram login credentials"
                return SessionValidationResult(
                    success=False,
                    credential_id=self.credential_id,
                    storage_state=self.storage_state,
                    message=message,
                    error=message,
                )

            login_flow = InstagramLoginFlow(
                self,
                login_username=self.login_username,
                password=self.password,
            )
            login_result = await login_flow.execute(page)
            if not login_result.success:
                return SessionValidationResult(
                    success=False,
                    credential_id=self.credential_id,
                    storage_state=self.storage_state,
                    message=login_result.message,
                    error=login_result.error or login_result.message,
                )

            await self._navigate_to_home(page)

            if not await self._has_logged_in_markers(page):
                message = "Unable to confirm authenticated session after login"
                return SessionValidationResult(
                    success=False,
                    credential_id=self.credential_id,
                    storage_state=self.storage_state,
                    message=message,
                    error=message,
                )

            self.logger.info(
                "Login validated for credential id=%s",
                credential.id,
            )
            persisted = await self._persist_storage_state()
            return SessionValidationResult(
                success=True,
                credential_id=self.credential_id,
                storage_state=persisted or self.storage_state,
                message="Instagram session refreshed via login",
            )

    def _apply_credential(self, credential: CredentialCandidate) -> None:
        self.credential_id = credential.id
        self.login_username = (credential.login_username or "").strip()
        self.password = ""
        self._encrypted_password = credential.encrypted_password
        self._apply_storage_state(credential.session)

    async def _load_credentials(self) -> list[CredentialCandidate]:
        collection = self._get_credentials_collection()
        docs = await list_ig_credentials(
            collection, skip=0, limit=MAX_CREDENTIALS_FETCH
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

    def _ensure_login_credentials(self, credential: CredentialCandidate) -> bool:
        if self.login_username and self.password:
            return True

        if not credential.login_username or not credential.encrypted_password:
            self.logger.warning(
                "Credential id=%s missing login_username or password",
                credential.id,
            )
            return False

        try:
            decrypted = decrypt_ig_password(credential.encrypted_password)
        except Exception as exc:
            self.logger.error(
                "Failed to decrypt Instagram password for id=%s: %s",
                credential.id,
                exc,
            )
            return False

        self.login_username = credential.login_username.strip()
        self.password = decrypted
        return bool(self.login_username and self.password)

    async def _persist_storage_state(self) -> dict[str, Any] | None:
        if self.context is None:
            return self.storage_state

        try:
            storage_state = await self.context.storage_state()
            state = dict(storage_state)
        except Exception as exc:  # pragma: no cover - IO variability
            self.logger.warning("Failed to capture storage state: %s", exc)
            return self.storage_state

        try:
            self._apply_storage_state(state)
        except Exception as exc:
            self.logger.warning("Failed to apply storage state: %s", exc)

        if self.credential_id:
            await self._persist_to_mongo(self.credential_id, state)
        else:
            self.logger.warning("Missing credential id; session not persisted to Mongo")

        return state

    async def _persist_to_mongo(
        self, credential_id: str, state: dict[str, Any]
    ) -> bool:
        """Helper para persistir en MongoDB con manejo de errores centralizado."""
        try:
            collection = self._get_credentials_collection()
            await update_ig_credential_session(collection, credential_id, state)
            self.logger.info(
                "Persisted Instagram session to Mongo for id=%s",
                credential_id,
            )
            return True
        except Exception as exc:  # pragma: no cover - persistence variability
            self.logger.error(
                "Failed to persist Instagram session for id=%s: %s",
                credential_id,
                exc,
            )
            return False

    def _get_credentials_collection(self):
        if self._credentials_collection is None:
            if _credentials_collection_resolver is not None:
                self._credentials_collection = _credentials_collection_resolver()
            else:
                from app.core.mongodb import get_mongo_kiizama_ig

                db = get_mongo_kiizama_ig()
                self._credentials_collection = db.get_collection("ig_credentials")
        return self._credentials_collection

    async def _navigate_to_home(self, page: Page) -> bool:
        try:
            await self.retryable_goto(
                page,
                "https://www.instagram.com/",
                wait_until="domcontentloaded",
                timeout=self.timeout_ms,
            )
        except Exception as exc:
            self.logger.error("Failed to navigate to Instagram home: %s", exc)
            return False

        try:
            await page.wait_for_load_state("domcontentloaded", timeout=5000)
        except Exception:
            pass

        return True

    async def _has_logged_in_markers(self, page: Page) -> bool:
        try:
            self.logger.info("Checking logged-in markers")

            # Marker 1: story tray (keep it but loosen it)
            story_tray = page.locator("div[data-pagelet='story_tray']")
            if await story_tray.first.is_visible(timeout=1500):
                self.logger.info("Story tray marker present")
            else:
                self.logger.info("Story tray marker not visible")

            # Marker 2: settings/menu button (avoid svg title checks)
            # Try a few common patterns; pick the first that appears.
            candidates = [
                page.get_by_role("button", name="Settings"),  # English
                page.get_by_role("button", name="Configuración"),  # Spanish
                page.locator("[aria-label='Settings']"),
                page.locator("[aria-label='Configuración']"),
                page.locator(
                    "a[aria-label*='Settings'], button[aria-label*='Settings']"
                ),
            ]

            for c in candidates:
                if await c.first.is_visible(timeout=1500):
                    self.logger.info(
                        "Settings/menu marker present: %s",
                        await c.first.get_attribute("aria-label"),
                    )
                    return True

            # If you want to require both markers, change logic accordingly.
            return await story_tray.first.is_visible(timeout=250)

        except PlaywrightTimeoutError:
            self.logger.info("Timeout while checking logged-in markers")
            return False
        except Exception as exc:
            self.logger.debug("Error checking login markers: %s", exc)
            return False


__all__ = [
    "InstagramSessionValidator",
    "SessionValidationResult",
    "configure_credentials_collection_resolver",
]
