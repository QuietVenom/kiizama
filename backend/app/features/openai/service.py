"""Service layer that orchestrates OpenAI response helpers."""

from __future__ import annotations

import os
from collections.abc import Callable, Mapping
from typing import Any

from .types import DEFAULT_OPENAI_BASE_URL, OpenAIResponseService

ServiceKwargs = Mapping[str, Any] | None
FunctionKwargs = Mapping[str, Any] | None

_SUPPORTED_OPTIONS: tuple[str, ...] = ("create_response", "stream_response")


def _clean_kwargs(values: Mapping[str, Any]) -> dict[str, Any]:
    """Drop ``None`` entries so OpenAI defaults remain untouched."""

    return {key: value for key, value in values.items() if value is not None}


class OpenAIService:
    """Delegate execution to :class:`OpenAIResponseService` helpers."""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        default_model: str | None = None,
        base_url: str | None = DEFAULT_OPENAI_BASE_URL,
        organization: str | None = None,
        project: str | None = None,
        timeout: int = 180,
        max_retries: int = 3,
        response_service_factory: Callable[..., OpenAIResponseService] | None = None,
        **extra_service_kwargs: Any,
    ) -> None:
        resolved_api_key = (
            api_key if api_key is not None else os.getenv("OPENAI_API_KEY")
        )

        base_kwargs = {
            "api_key": resolved_api_key,
            "default_model": default_model,
            "base_url": base_url,
            "organization": organization,
            "project": project,
            "timeout": timeout,
            "max_retries": max_retries,
        }

        combined_kwargs = {**base_kwargs, **extra_service_kwargs}
        self._service_defaults = _clean_kwargs(combined_kwargs)
        self._response_service_factory = response_service_factory

    @property
    def supported_options(self) -> tuple[str, ...]:
        """Expose the supported function options for discovery or validation."""

        return _SUPPORTED_OPTIONS

    def execute(
        self,
        option: str,
        *,
        function_kwargs: FunctionKwargs = None,
        service_overrides: ServiceKwargs = None,
    ) -> Any:
        """Execute one of the supported OpenAI helpers.

        Args:
            option: Name of the helper (e.g. ``"create_response"``).
            function_kwargs: Parameters forwarded to the helper method.
            service_overrides: Optional overrides for constructing
                :class:`OpenAIResponseService` instances.

        Returns:
            Depends on the selected option.

        Raises:
            ValueError: If the option is unsupported or mis-configured.
        """

        if option not in _SUPPORTED_OPTIONS:
            supported = ", ".join(_SUPPORTED_OPTIONS)
            raise ValueError(f"Unsupported option '{option}'. Choose from: {supported}")

        fn_kwargs = dict(function_kwargs or {})
        overrides = dict(service_overrides or {})

        return self._execute_method(option, fn_kwargs, overrides)

    def _execute_method(
        self,
        option: str,
        function_kwargs: dict[str, Any],
        overrides: dict[str, Any],
    ) -> Any:
        """Execute the specified method on response service."""

        with self._create_response_service(overrides) as response_service:
            method = getattr(response_service, option, None)
            if not callable(method):
                raise ValueError(
                    f"Option '{option}' is not callable on response service"
                )
            return method(**function_kwargs)

    def _create_response_service(
        self,
        overrides: Mapping[str, Any] | None = None,
    ) -> OpenAIResponseService:
        """Instantiate the underlying :class:`OpenAIResponseService`."""

        overrides_dict = _clean_kwargs(dict(overrides or {}))
        merged_kwargs = {**self._service_defaults, **overrides_dict}

        # Use the provided factory or the class itself
        factory = self._response_service_factory or OpenAIResponseService
        return factory(**merged_kwargs)


# Backwards-compatible alias until callers switch to the new name.
FeatureTemplateService = OpenAIService


__all__ = ["OpenAIService", "FeatureTemplateService"]
