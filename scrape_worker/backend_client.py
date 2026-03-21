from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx
from kiizama_scrape_core.ig_scraper.schemas import (
    InstagramScrapeJobTerminalizationRequest,
    InstagramScrapeJobTerminalizationResponse,
)

from scrape_worker.config import get_settings


@dataclass(slots=True)
class WorkerBackendCompletionResult:
    status_code: int
    payload: InstagramScrapeJobTerminalizationResponse | None = None
    raw_body: dict[str, Any] | None = None


class ScrapeWorkerBackendClient:
    def __init__(self, *, base_url: str) -> None:
        self._base_url = base_url.rstrip("/")
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            timeout=httpx.Timeout(30.0),
        )
        self._access_token: str | None = None

    async def aclose(self) -> None:
        await self._client.aclose()

    async def complete_job(
        self,
        *,
        job_id: str,
        payload: InstagramScrapeJobTerminalizationRequest,
    ) -> WorkerBackendCompletionResult:
        response = await self._post_with_auth(
            f"/api/v1/internal/ig-scraper/jobs/{job_id}/complete",
            json=payload.model_dump(mode="json"),
        )
        body = self._parse_json(response)

        parsed: InstagramScrapeJobTerminalizationResponse | None = None
        if response.status_code == 200 and isinstance(body, dict):
            parsed = InstagramScrapeJobTerminalizationResponse.model_validate(body)
        elif response.status_code == 409 and isinstance(body, dict):
            detail = body.get("detail")
            if isinstance(detail, dict):
                parsed = InstagramScrapeJobTerminalizationResponse.model_validate(
                    detail
                )

        return WorkerBackendCompletionResult(
            status_code=response.status_code,
            payload=parsed,
            raw_body=body if isinstance(body, dict) else None,
        )

    async def _post_with_auth(
        self, path: str, *, json: dict[str, Any]
    ) -> httpx.Response:
        if self._access_token is None:
            self._access_token = await self._login()

        response = await self._client.post(
            path,
            json=json,
            headers={"Authorization": f"Bearer {self._access_token}"},
        )
        if response.status_code not in {401, 403}:
            return response

        self._access_token = await self._login()
        return await self._client.post(
            path,
            json=json,
            headers={"Authorization": f"Bearer {self._access_token}"},
        )

    async def _login(self) -> str:
        settings = get_settings()
        response = await self._client.post(
            "/api/v1/internal/login/access-token",
            data={
                "username": settings.system_admin_email,
                "password": settings.system_admin_password,
            },
        )
        response.raise_for_status()
        body = self._parse_json(response)
        if not isinstance(body, dict) or not isinstance(body.get("access_token"), str):
            raise RuntimeError("Worker backend login returned an invalid payload.")
        return body["access_token"]

    @staticmethod
    def _parse_json(response: httpx.Response) -> Any:
        if not response.content:
            return None
        return response.json()


__all__ = ["ScrapeWorkerBackendClient", "WorkerBackendCompletionResult"]
