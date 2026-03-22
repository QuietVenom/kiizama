from __future__ import annotations

import asyncio
from collections import deque
from dataclasses import asdict, dataclass
from typing import Any, Literal

from ..classes import InstagramScrapeResult, SessionValidationResult
from ..config import get_default_max_concurrent
from ..constants import DEFAULT_USER_AGENT
from ..metrics import calculate_metrics_from_scrape
from ..schemas import InstagramBatchScrapeRequest
from .base import BaseInstagramWorker
from .scrape_collector import InstagramScrapeCollector
from .session_validator import InstagramSessionValidator

BatchScrapeModeName = Literal["snapshot", "recommendations"]


@dataclass(frozen=True, slots=True)
class BatchScrapeModeConfig:
    name: BatchScrapeModeName
    collect_posts: bool
    collect_reels: bool
    collect_recommendations: bool
    include_metrics: bool


SNAPSHOT_MODE = BatchScrapeModeConfig(
    name="snapshot",
    collect_posts=True,
    collect_reels=True,
    collect_recommendations=False,
    include_metrics=True,
)
RECOMMENDATIONS_MODE = BatchScrapeModeConfig(
    name="recommendations",
    collect_posts=False,
    collect_reels=False,
    collect_recommendations=True,
    include_metrics=False,
)
_MODE_CONFIG_MAP: dict[BatchScrapeModeName, BatchScrapeModeConfig] = {
    SNAPSHOT_MODE.name: SNAPSHOT_MODE,
    RECOMMENDATIONS_MODE.name: RECOMMENDATIONS_MODE,
}


class InstagramBatchScraper(BaseInstagramWorker):
    """Procesa múltiples perfiles de Instagram en lote con paralelismo controlado."""

    def __init__(
        self,
        usernames: list[str],
        max_posts: int = 12,
        headless: bool = True,
        user_agent: str = DEFAULT_USER_AGENT,
        locale: str = "en-US",
        proxy: str | None = None,
        timeout_ms: int = 30000,
        max_concurrent: int | None = None,
        login_username: str | None = None,
        password: str | None = None,
        recommended_limit: int | None = 10,
        measure_network_bytes: bool = False,
        lean_mode: bool | None = None,
        snapshot_mode: bool = False,
        recommendations_mode: bool = False,
        mode: BatchScrapeModeName | str | None = None,
    ) -> None:
        super().__init__(
            headless=headless,
            user_agent=user_agent,
            locale=locale,
            proxy=proxy,
            timeout_ms=timeout_ms,
            measure=False,
            measure_network_bytes=measure_network_bytes,
        )

        self.usernames = [
            username.strip().lower() for username in usernames if username.strip()
        ]
        self.max_posts = max_posts
        self.max_concurrent = (
            get_default_max_concurrent() if max_concurrent is None else max_concurrent
        )
        self.login_username = (login_username or "").strip()
        self.password = password or ""
        self._requested_user_agent = user_agent or DEFAULT_USER_AGENT
        self.recommended_limit = recommended_limit
        self.mode_config = self._resolve_mode(
            mode=mode,
            snapshot_mode=snapshot_mode,
            recommendations_mode=recommendations_mode,
            lean_mode=lean_mode,
        )

        # Cola de perfiles pendientes
        self.profile_queue = deque(self.usernames)

        # Contadores de resultados
        self.results: dict[str, InstagramScrapeResult] = {}
        self.counters = {
            "requested": len(self.usernames),
            "successful": 0,
            "failed": 0,
            "not_found": 0,
        }

        # Estado interno
        self._raw_state: dict[str, Any] = {}
        self.extra_headers: dict[str, str] = {}
        self.storage_state: dict[str, Any] | None = None
        self.credential_id: str | None = None
        self._apply_storage_state_info()

    @property
    def mode(self) -> BatchScrapeModeName:
        return self.mode_config.name

    @property
    def is_recommendations_mode(self) -> bool:
        return self.mode == "recommendations"

    @staticmethod
    def _resolve_mode(
        *,
        mode: BatchScrapeModeName | str | None,
        snapshot_mode: bool,
        recommendations_mode: bool,
        lean_mode: bool | None,
    ) -> BatchScrapeModeConfig:
        candidates: list[BatchScrapeModeName] = []

        if mode is not None:
            normalized_mode = str(mode).strip().lower()
            if normalized_mode not in _MODE_CONFIG_MAP:
                raise ValueError("Invalid mode. Use 'snapshot' or 'recommendations'.")
            candidates.append(
                "snapshot" if normalized_mode == "snapshot" else "recommendations"
            )

        if snapshot_mode:
            candidates.append("snapshot")

        if recommendations_mode:
            candidates.append("recommendations")

        if lean_mode is not None:
            candidates.append("recommendations" if lean_mode else "snapshot")

        if not candidates:
            return SNAPSHOT_MODE

        unique_candidates = set(candidates)
        if len(unique_candidates) > 1:
            raise ValueError(
                "Conflicting scraper modes provided. Set only one of "
                "snapshot_mode=True, recommendations_mode=True, mode=..., or lean_mode."
            )

        selected_mode = candidates[0]
        return _MODE_CONFIG_MAP[selected_mode]

    @classmethod
    def create_snapshot(
        cls,
        **kwargs: Any,
    ) -> InstagramBatchScraper:
        kwargs.pop("recommended_limit", None)
        return cls(**kwargs, snapshot_mode=True)

    @classmethod
    def create_recommendations(
        cls,
        **kwargs: Any,
    ) -> InstagramBatchScraper:
        return cls(**kwargs, recommendations_mode=True)

    # ------------------------------------------------------------------
    # Storage state helpers
    # ------------------------------------------------------------------
    def _apply_storage_state_info(
        self,
        *,
        storage_state: dict[str, Any] | None = None,
    ) -> None:
        self.storage_state = storage_state or None
        self._raw_state = storage_state or {}

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

    # ------------------------------------------------------------------
    # Overrides
    # ------------------------------------------------------------------
    def build_context_options(self) -> dict[str, Any]:
        options = super().build_context_options()
        if self.storage_state:
            options["storage_state"] = self.storage_state
        if self.extra_headers:
            options["extra_http_headers"] = self.extra_headers
        options["viewport"] = {"width": 1920, "height": 1080}
        return options

    async def _ensure_session_ready(self) -> SessionValidationResult:
        validator = InstagramSessionValidator(
            login_username=self.login_username or None,
            password=self.password or None,
            headless=self.headless,
            user_agent=self._requested_user_agent,
            locale=self.locale,
            proxy=self.proxy,
            timeout_ms=self.timeout_ms,
            measure_network_bytes=self.measure_network_bytes,
            network_usage=self.network_usage,
        )
        result = await validator.ensure_session()
        if result.success:
            self.credential_id = result.credential_id
            if result.storage_state:
                self._apply_storage_state_info(storage_state=result.storage_state)
        return result

    # ------------------------------------------------------------------
    # Método principal de procesamiento por lotes con deque
    # ------------------------------------------------------------------
    async def run(self) -> dict[str, Any]:
        """Ejecuta el scraping por lotes usando una cola (deque) para manejar los perfiles."""
        if not self.usernames:
            result = {
                "results": {},
                "counters": dict(self.counters),
                "error": "No usernames provided",
            }
            if self.measure_network_bytes:
                result["network_usage"] = self.get_network_usage()
            return result

        session_result = await self._ensure_session_ready()
        if not session_result.success:
            self.counters["failed"] = self.counters["requested"]
            result = {
                "results": {},
                "counters": dict(self.counters),
                "error": session_result.error or session_result.message,
            }
            if self.measure_network_bytes:
                result["network_usage"] = self.get_network_usage()
            return result

        async with self:
            # Crear workers que procesen la cola
            workers = []
            for i in range(min(self.max_concurrent, len(self.profile_queue))):
                worker = asyncio.create_task(self._profile_worker(f"worker-{i + 1}"))
                workers.append(worker)

            # Esperar a que todos los workers terminen
            await asyncio.gather(*workers)

        serialized_results: dict[str, dict[str, Any]] = {}
        for username, profile_result in self.results.items():
            result_dict = asdict(profile_result)
            if self.mode_config.include_metrics:
                try:
                    metrics = calculate_metrics_from_scrape(result_dict)
                except Exception as exc:  # pragma: no cover - métricas defensivas
                    self.logger.warning(
                        "Failed to calculate metrics for %s: %s", username, exc
                    )
                    metrics = calculate_metrics_from_scrape({})
                result_dict["metrics"] = metrics
            serialized_results[username] = result_dict

        result = {"results": serialized_results, "counters": dict(self.counters)}
        if self.measure_network_bytes:
            network_usage = self.get_network_usage()
            result["network_usage"] = network_usage
            self.logger.info(
                (
                    "Playwright downloaded bytes (session validation + scrape): %s "
                    "(responses=%s, measurement_errors=%s)"
                ),
                network_usage["downloaded_bytes_total"],
                network_usage["responses_total"],
                network_usage["responses_failed_to_measure"],
            )
        return result

    async def _profile_worker(self, worker_name: str) -> None:
        """Worker que procesa perfiles de la cola hasta que esté vacía."""
        self.logger.info(f"{worker_name} started, processing queue")

        while self.profile_queue:
            try:
                # Obtener el siguiente perfil de la cola (FIFO)
                username = self.profile_queue.popleft()
                self.logger.info(f"{worker_name} processing: {username}")

                await self._scrape_single_profile(username)

            except IndexError:
                # La cola está vacía
                break
            except Exception as exc:
                self.logger.error(f"{worker_name} error processing profile: {exc}")
                continue

        self.logger.info(f"{worker_name} finished, queue empty")

    async def _scrape_single_profile(self, username: str) -> None:
        """Scrapea un único perfil de la cola."""
        try:
            # Crear una nueva página para este perfil
            context = self.context
            if context is None:
                raise RuntimeError("Browser context is not initialized")

            page = await context.new_page()
            await self.add_stealth(page)

            result = await self._scrape_profile_page(page, username)
            self.results[username] = result

            if not result.success and not result.error:
                result.error = "Unable to scrape this profile"

            # Actualizar contadores
            if result.success:
                self.counters["successful"] += 1
                self.logger.info(f"✓ Successfully scraped {username}")
            else:
                if result.error == "Instagram username does not exist":
                    self.counters["not_found"] += 1
                    self.logger.warning(f"✗ Profile not found: {username}")
                else:
                    self.counters["failed"] += 1
                    self.logger.error(f"✗ Failed to scrape {username}: {result.error}")

            await page.close()

        except Exception as exc:
            self.logger.error(f"Error scraping {username}: {exc}")
            error_result = InstagramScrapeResult(
                success=False, error=f"Scraping error: {exc}"
            )
            self.results[username] = error_result
            self.counters["failed"] += 1

    async def _scrape_profile_page(
        self, page: Any, username: str
    ) -> InstagramScrapeResult:
        """Lógica de scraping para un perfil individual."""
        scrape_result = InstagramScrapeResult()
        collector = InstagramScrapeCollector(
            self,
            self.max_posts,
            target_username=username,
            # TEMP: Pass recommendation cap to collector to cut parsing work earlier.
            recommended_limit=self.recommended_limit,
            collect_posts=self.mode_config.collect_posts,
            collect_reels=self.mode_config.collect_reels,
            collect_recommendations=self.mode_config.collect_recommendations,
        )

        collector.attach(page)

        try:
            profile_url = f"https://www.instagram.com/{username}/"

            # Navegar al perfil
            try:
                await self.retryable_goto(
                    page,
                    profile_url,
                    wait_until="domcontentloaded",
                    timeout=self.timeout_ms,
                )
            except Exception as exc:
                self.logger.error(
                    "Error loading profile %s after retries: %s", username, exc
                )
                scrape_result.error = f"Error loading profile after retries: {exc}"
                return scrape_result

            # Verificar si el perfil existe
            if await self.profile_not_found(page):
                scrape_result.error = "Instagram username does not exist"
                scrape_result.success = False
                return scrape_result

            if self.is_recommendations_mode:
                try:
                    await asyncio.wait_for(
                        collector.recommendations_ready_event.wait(),
                        timeout=min(self.timeout_ms / 1000, 8),
                    )
                except asyncio.TimeoutError:
                    try:
                        await page.reload(
                            wait_until="domcontentloaded",
                            timeout=self.timeout_ms,
                        )
                        await asyncio.wait_for(
                            collector.recommendations_ready_event.wait(),
                            timeout=3,
                        )
                    except Exception as refresh_exc:
                        self.logger.debug(
                            "Refresh after recommendations timeout failed: %s",
                            refresh_exc,
                        )
                    self.logger.warning(
                        "Timeout waiting for recommendations data for %s", username
                    )
                    if await self.profile_not_found(
                        page, timeout_ms=min(self.timeout_ms, 2000)
                    ):
                        scrape_result.error = "Instagram username does not exist"
                        scrape_result.success = False
                        return scrape_result
            else:
                # Esperar datos capturados por GraphQL
                posts_ready = False
                try:
                    await asyncio.wait_for(
                        collector.posts_ready_event.wait(),
                        timeout=self.timeout_ms / 1000,
                    )
                    posts_ready = True
                except asyncio.TimeoutError:
                    try:
                        await page.reload(
                            wait_until="domcontentloaded",
                            timeout=self.timeout_ms,
                        )
                        await asyncio.wait_for(
                            collector.posts_ready_event.wait(), timeout=5
                        )
                        posts_ready = True
                    except Exception as refresh_exc:
                        self.logger.debug(
                            "Refresh after GraphQL timeout failed: %s", refresh_exc
                        )
                    self.logger.warning(
                        "Timeout waiting for GraphQL data for %s", username
                    )
                    if await self.profile_not_found(
                        page, timeout_ms=min(self.timeout_ms, 2000)
                    ):
                        scrape_result.error = "Instagram username does not exist"
                        scrape_result.success = False
                        return scrape_result

                if posts_ready:
                    # Recolectar reels
                    try:
                        await self.collect_reels_tab(
                            page, username, collector.reels_done_event
                        )
                    except asyncio.TimeoutError:
                        self.logger.warning(
                            "Timeout waiting for reels data for %s", username
                        )
                else:
                    self.logger.info(
                        "Skipping reels collection for %s due to missing GraphQL data",
                        username,
                    )

        except Exception as exc:
            self.logger.error("Error during profile scraping for %s: %s", username, exc)
            scrape_result.error = f"Error during profile scraping: {exc}"
            scrape_result.success = False
        finally:
            collector.detach(page)

        # Fallback para datos de usuario si el collector no los capturó
        if not collector.user_info:
            try:
                script_content = await page.evaluate(
                    """
                    () => {
                        const scripts = document.querySelectorAll('script[type="application/json"]');
                        for (const script of scripts) {
                            try {
                                const data = JSON.parse(script.textContent);
                                if (data.entry_data && data.entry_data.ProfilePage) {
                                    return data;
                                }
                            } catch (e) {}
                        }
                        return null;
                    }
                    """
                )
                if script_content:
                    profile_pages = self.dig(script_content, "entry_data.ProfilePage")
                    if (
                        profile_pages
                        and isinstance(profile_pages, list)
                        and profile_pages
                    ):
                        user_data = self.dig(profile_pages[0], "graphql.user")
                        if isinstance(user_data, dict):
                            collector.user_info = user_data
            except Exception as exc:
                self.logger.warning(
                    "Failed to extract user info via fallback for %s: %s", username, exc
                )

        # Construir resultado final
        scrape_result.user = self.parse_user_info(collector.user_info or {})
        if self.mode_config.collect_recommendations:
            if self.recommended_limit is None:
                scrape_result.recommended_users = collector.recommended_users
            else:
                scrape_result.recommended_users = collector.recommended_users[
                    : self.recommended_limit
                ]
        else:
            scrape_result.recommended_users = []

        if self.is_recommendations_mode:
            scrape_result.posts = []
            scrape_result.reels = []
            has_recommendations = bool(scrape_result.recommended_users)
            has_profile_identity = bool(scrape_result.user.username)
            scrape_result.success = scrape_result.error is None and (
                has_recommendations or has_profile_identity
            )
            if not scrape_result.success and scrape_result.error is None:
                if await self.profile_not_found(page):
                    scrape_result.error = "Instagram username does not exist"
                else:
                    scrape_result.error = (
                        "No recommendations were collected for this profile"
                    )
        else:
            scrape_result.posts = collector.posts
            scrape_result.reels = collector.reels
            scrape_result.success = bool(scrape_result.user.username)
            if not scrape_result.success and scrape_result.error is None:
                if await self.profile_not_found(page):
                    scrape_result.error = "Instagram username does not exist"
                else:
                    scrape_result.error = (
                        "Unable to collect profile data for this username"
                    )

        return scrape_result

    def get_queue_status(self) -> dict[str, Any]:
        """Retorna el estado actual de la cola."""
        return {
            "pending": len(self.profile_queue),
            "processed": len(self.results),
            "queue_contents": list(self.profile_queue),
        }


async def scrape_multiple_profiles(
    request: InstagramBatchScrapeRequest | dict[str, Any],
) -> dict[str, Any]:
    """Función de alto nivel para scraping por lotes."""
    if not isinstance(request, InstagramBatchScrapeRequest):
        request = InstagramBatchScrapeRequest(**request)

    scraper = InstagramBatchScraper.create_snapshot(
        usernames=request.usernames,
        max_posts=request.max_posts,
        headless=request.headless,
        max_concurrent=request.max_concurrent,
        timeout_ms=request.timeout_ms,
        user_agent=request.user_agent,
        locale=request.locale,
        proxy=request.proxy,
        measure_network_bytes=request.measure_network_bytes,
    )

    return await scraper.run()


__all__ = ["InstagramBatchScraper", "scrape_multiple_profiles"]
