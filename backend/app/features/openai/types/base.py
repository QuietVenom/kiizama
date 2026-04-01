from __future__ import annotations

import logging
from collections.abc import Callable, Generator, Mapping
from typing import TYPE_CHECKING, Any, Literal, TypedDict, cast

from openai import APIStatusError, OpenAI, OpenAIError
from typing_extensions import NotRequired

if TYPE_CHECKING:  # pragma: no cover - imported for type checking only
    from openai.types.responses import ResponseInputParam
else:
    ResponseInputParam = Any

logger = logging.getLogger(__name__)

DEFAULT_OPENAI_BASE_URL = "https://api.openai.com/v1"
DEFAULT_MODEL = "gpt-5.4-mini"

MessageDict = dict[Literal["role", "content"], str]


class ErrorInfo(TypedDict):
    status_code: int
    message: str
    error_type: NotRequired[str]
    error_code: NotRequired[str]
    error_param: NotRequired[str]
    raw: NotRequired[Mapping[str, Any]]


class OpenAIResponseError(RuntimeError):
    """Custom exception for OpenAI API errors."""

    def __init__(
        self,
        *,
        status_code: int,
        message: str,
        error_type: str | None = None,
        error_code: str | None = None,
        error_param: str | None = None,
        raw: Mapping[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.error_type = error_type
        self.error_code = error_code
        self.error_param = error_param
        self.raw: Mapping[str, Any] = raw or {}


class OpenAIResponseService:
    """
    Robust class to handle calls to OpenAI's `responses` endpoint.
    Includes error handling, validation and support for different input types.
    """

    def __init__(
        self,
        api_key: str | None = None,
        default_model: str = DEFAULT_MODEL,
        base_url: str | None = DEFAULT_OPENAI_BASE_URL,
        organization: str | None = None,
        project: str | None = None,
        client: OpenAI | None = None,
        timeout: int = 30,
        max_retries: int = 3,
    ) -> None:
        """
        Initialize OpenAI Responses service.

        Args:
            api_key: OpenAI API key (optional if client is provided)
            default_model: Default model to use
            base_url: API base URL
            organization: OpenAI organization
            project: OpenAI project
            client: Preconfigured OpenAI client
            timeout: Request timeout in seconds
            max_retries: Maximum number of retries
        """
        if client is None and api_key is None:
            raise ValueError("Either api_key or preconfigured client is required")

        client_kwargs: dict[str, Any] = {}
        if api_key is not None:
            client_kwargs["api_key"] = api_key
        if base_url:
            client_kwargs["base_url"] = base_url.rstrip("/")
        if organization:
            client_kwargs["organization"] = organization
        if project:
            client_kwargs["project"] = project

        client_kwargs["timeout"] = timeout
        client_kwargs["max_retries"] = max_retries

        self._client = client or OpenAI(**client_kwargs)
        self.default_model = default_model

    def create_response(
        self,
        prompt: str | list[MessageDict],
        model: str | None = None,
        temperature: float | None = None,
        max_output_tokens: int | None = None,
        metadata: dict[str, Any] | None = None,
        tools: list[dict[str, Any]] | None = None,
        file_ids: list[str] | None = None,
        reasoning: dict[str, Any] | None = None,
        system_prompt: str | None = None,
        extra_headers: dict[str, str] | None = None,
        response_format: dict[str, Any] | None = None,
        text: dict[str, Any] | None = None,
        tool_choice: Any = None,
        include: list[str] | None = None,
    ) -> str:
        """
        Call the `responses` service and return generated text.

        Args:
            prompt: Prompt as string or list of messages
            model: Model to use (uses default_model if None)
            temperature: Temperature for sampling
            max_output_tokens: Maximum output tokens
            metadata: Additional metadata
            tools: Available tools/functions
            file_ids: File IDs to include
            reasoning: Reasoning configuration
            system_prompt: System prompt (overrides system messages)
            extra_headers: Additional headers
            response_format: Response format configuration (e.g. enforce JSON)

        Returns:
            Generated text from the model

        Raises:
            OpenAIResponseError: If API error occurs
            ValueError: If parameters are invalid
        """
        raw_response_kwargs = {
            "prompt": prompt,
            "model": model,
            "temperature": temperature,
            "max_output_tokens": max_output_tokens,
            "metadata": metadata,
            "tools": tools,
            "file_ids": file_ids,
            "reasoning": reasoning,
            "system_prompt": system_prompt,
            "extra_headers": extra_headers,
            "response_format": response_format,
            "text": text,
            "tool_choice": tool_choice,
            "include": include,
        }

        try:
            response = self._create_raw_response(**raw_response_kwargs)
            return self._extract_output_text(response)

        except APIStatusError as exc:
            if temperature is not None and self._is_temperature_unsupported_error(exc):
                logger.warning(
                    "Model '%s' rejected temperature. Retrying without temperature.",
                    model or self.default_model,
                )
                raw_response_kwargs["temperature"] = None
                try:
                    response = self._create_raw_response(**raw_response_kwargs)
                    return self._extract_output_text(response)
                except APIStatusError as retry_exc:
                    exc = retry_exc

            error_info = self._parse_error_response(exc)
            logger.error(f"OpenAI API error: {error_info}")
            raw_payload = error_info.get("raw")
            if raw_payload is not None:
                logger.error("OpenAI API raw response: %s", raw_payload)
            raise OpenAIResponseError(**error_info) from exc

        except OpenAIError as exc:
            raw_payload = self._wrap_raw_payload(self._get_raw_response(exc))
            if raw_payload is not None:
                logger.error("OpenAI client raw response: %s", raw_payload)
            logger.error(f"OpenAI error: {str(exc)}")
            raise OpenAIResponseError(
                status_code=500,
                message=f"OpenAI client error: {str(exc)}",
                raw=raw_payload,
            ) from exc

    def _create_raw_response(
        self,
        prompt: str | list[MessageDict],
        model: str | None = None,
        temperature: float | None = None,
        max_output_tokens: int | None = None,
        metadata: dict[str, Any] | None = None,
        tools: list[dict[str, Any]] | None = None,
        file_ids: list[str] | None = None,
        reasoning: dict[str, Any] | None = None,
        system_prompt: str | None = None,
        extra_headers: dict[str, str] | None = None,
        response_format: dict[str, Any] | None = None,
        text: dict[str, Any] | None = None,
        tool_choice: Any = None,
        include: list[str] | None = None,
    ) -> Any:
        """Internal method to create raw response."""
        model = self._validate_model(model)
        input_content = self._build_input(prompt, system_prompt)

        request_kwargs: dict[str, Any] = {
            "model": model,
            "input": input_content,
        }
        if temperature is not None:
            request_kwargs["temperature"] = temperature

        # Add optional parameters
        optional_params = {
            "max_output_tokens": max_output_tokens,
            "metadata": metadata,
            "tools": tools,
            "file_ids": file_ids,
            "reasoning": reasoning,
            "extra_headers": extra_headers,
            "response_format": response_format,
            "text": text,
            "tool_choice": tool_choice,
            "include": include,
        }

        for key, value in optional_params.items():
            if value is not None:
                request_kwargs[key] = value

        return self._client.responses.create(**request_kwargs)

    def _validate_model(self, model: str | None) -> str:
        """Validate that a valid model is available."""
        model = model or self.default_model
        if not model:
            raise ValueError("A model must be specified for OpenAI")
        return model

    def _build_input(
        self, prompt: str | list[MessageDict], system_prompt: str | None = None
    ) -> ResponseInputParam:
        """Build input in message format."""
        messages: list[MessageDict]
        if isinstance(prompt, str):
            messages = [{"role": "user", "content": prompt}]
        elif isinstance(prompt, list) and all(
            isinstance(msg, dict) and "role" in msg and "content" in msg
            for msg in prompt
        ):
            messages = prompt.copy()
        else:
            raise ValueError(
                "Prompt must be string or list of dicts with 'role' and 'content'"
            )

        # Add system prompt if specified
        if system_prompt:
            system_message: MessageDict = {"role": "system", "content": system_prompt}
            # Insert at beginning or replace existing system message
            for i, msg in enumerate(messages):
                if msg.get("role") == "system":
                    messages[i] = system_message
                    break
            else:
                messages.insert(0, system_message)

        return cast(ResponseInputParam, messages)

    def _extract_output_text(self, response: Any) -> str:
        """Robustly extract text from response."""
        try:
            direct_text = self._coerce_text_value(
                getattr(response, "output_text", None)
            )
            if direct_text:
                return direct_text

            outputs = getattr(response, "output", None) or []
            for output in outputs:
                output_text = self._coerce_text_value(getattr(output, "text", None))
                if output_text:
                    return output_text

                contents = getattr(output, "content", None) or []
                for content in contents:
                    content_text = self._coerce_text_value(
                        getattr(content, "text", None)
                    )
                    if content_text:
                        return content_text

                    content_mapping = self._to_mapping(content)
                    if content_mapping:
                        mapped_text = self._extract_text_from_mapping(content_mapping)
                        if mapped_text:
                            return mapped_text

            response_mapping = self._to_mapping(response)
            if response_mapping:
                mapped_text = self._extract_text_from_mapping(response_mapping)
                if mapped_text:
                    return mapped_text

            logger.warning(
                "Empty response or no valid content. Raw response: %s", response
            )
            return ""

        except (
            Exception
        ) as exc:  # pragma: no cover - defensive guard for SDK shape changes
            logger.error(
                "Error extracting text from response: %s. Raw response: %s",
                exc,
                response,
            )
            return ""

    @classmethod
    def _extract_text_from_mapping(cls, payload: Mapping[str, Any]) -> str | None:
        for key in ("output_text", "text", "value", "content"):
            text = cls._coerce_text_value(payload.get(key))
            if text:
                return text

        outputs = payload.get("output")
        if isinstance(outputs, list | tuple):
            for item in outputs:
                text = cls._coerce_text_value(item)
                if text:
                    return text

        return None

    @classmethod
    def _coerce_text_value(cls, value: Any) -> str | None:
        if value is None:
            return None

        if isinstance(value, str):
            stripped = value.strip()
            return stripped or None

        if isinstance(value, int | float | bool):
            return str(value)

        if isinstance(value, Mapping):
            return cls._extract_text_from_mapping(value)

        if isinstance(value, list | tuple):
            fragments = [
                fragment for item in value if (fragment := cls._coerce_text_value(item))
            ]
            if not fragments:
                return None
            merged = "".join(fragments).strip()
            return merged or None

        nested_text = getattr(value, "text", None)
        if nested_text is not None and nested_text is not value:
            return cls._coerce_text_value(nested_text)

        dumped = cls._to_mapping(value)
        if dumped is not None:
            return cls._extract_text_from_mapping(dumped)

        return None

    @staticmethod
    def _to_mapping(value: Any) -> Mapping[str, Any] | None:
        if isinstance(value, Mapping):
            return value

        if not callable(getattr(value, "model_dump", None)):
            return None

        try:
            dumped = value.model_dump(mode="python")
        except TypeError:
            dumped = value.model_dump()
        except Exception:
            return None

        return dumped if isinstance(dumped, Mapping) else None

    def _parse_error_response(self, exc: APIStatusError) -> ErrorInfo:
        """Parse API error response."""
        base_info: ErrorInfo = {
            "status_code": exc.status_code,
            "message": str(exc),
        }

        try:
            payload = exc.response.json()
            base_info["raw"] = payload

            # Extract specific error information if available
            if isinstance(payload, dict) and "error" in payload:
                error = payload["error"]
                if isinstance(error, Mapping):
                    message = error.get("message")
                    if isinstance(message, str):
                        base_info["message"] = message
                    elif message is not None:
                        base_info["message"] = str(message)

                    error_type = error.get("type")
                    if isinstance(error_type, str):
                        base_info["error_type"] = error_type

                    error_code = error.get("code")
                    if isinstance(error_code, str):
                        base_info["error_code"] = error_code

                    error_param = error.get("param")
                    if isinstance(error_param, str):
                        base_info["error_param"] = error_param

        except ValueError:
            base_info["raw"] = {"raw_response": exc.response.text}

        return base_info

    @staticmethod
    def _get_raw_response(exc: OpenAIError) -> Mapping[str, Any] | str | None:
        """Extract the raw response payload from an OpenAI error if available."""
        response = getattr(exc, "response", None)
        if response is None:
            return None

        try:
            parsed = response.json()
            if isinstance(parsed, Mapping):
                return parsed
            if isinstance(parsed, str):
                return parsed
            return str(parsed)
        except Exception:
            pass

        text_value = getattr(response, "text", None)
        if text_value is not None:
            try:
                value = text_value() if callable(text_value) else text_value
            except Exception:
                pass
            else:
                if isinstance(value, Mapping) or isinstance(value, str):
                    return value
                return str(value)

        try:
            return str(response)
        except Exception:
            return None

    @staticmethod
    def _wrap_raw_payload(
        raw_payload: Mapping[str, Any] | str | None,
    ) -> Mapping[str, Any] | None:
        """Coerce the raw payload into a mapping so it can be logged and propagated."""
        if raw_payload is None:
            return None

        if isinstance(raw_payload, Mapping):
            return raw_payload

        return {"raw_response": raw_payload}

    def stream_response(
        self,
        prompt: str | list[MessageDict],
        model: str | None = None,
        temperature: float | None = None,
        system_prompt: str | None = None,
        on_delta: Callable[[str], None] | None = None,
    ) -> Generator[str, None, None]:
        """
        Streaming version of the response.

        Args:
            prompt: Prompt as string or list of messages
            model: Model to use
            temperature: Temperature for sampling
            system_prompt: System prompt
            on_delta: Optional callback to process each delta

        Yields:
            Text fragments as they are generated
        """
        model = self._validate_model(model)
        input_content = self._build_input(prompt, system_prompt)
        request_kwargs: dict[str, Any] = {
            "model": model,
            "input": input_content,
        }
        if temperature is not None:
            request_kwargs["temperature"] = temperature

        try:
            with self._client.responses.stream(**request_kwargs) as stream:
                for event in stream:
                    if event.type == "response.output_text.delta":
                        delta = event.delta
                        if on_delta:
                            on_delta(delta)
                        yield delta

        except APIStatusError as exc:
            if (
                temperature is not None
                and "temperature" in request_kwargs
                and self._is_temperature_unsupported_error(exc)
            ):
                logger.warning(
                    "Model '%s' rejected temperature in stream mode. "
                    "Retrying without temperature.",
                    model or self.default_model,
                )
                retry_kwargs = dict(request_kwargs)
                retry_kwargs.pop("temperature", None)
                try:
                    with self._client.responses.stream(**retry_kwargs) as stream:
                        for event in stream:
                            if event.type == "response.output_text.delta":
                                delta = event.delta
                                if on_delta:
                                    on_delta(delta)
                                yield delta
                    return
                except APIStatusError as retry_exc:
                    exc = retry_exc

            error_info = self._parse_error_response(exc)
            logger.error(f"Streaming error: {error_info}")
            raise OpenAIResponseError(**error_info) from exc

    def _is_temperature_unsupported_error(self, exc: APIStatusError) -> bool:
        """Detect API responses that reject the `temperature` parameter."""
        error_info = self._parse_error_response(exc)
        if error_info.get("error_param") != "temperature":
            return False

        message = str(error_info.get("message", "")).lower()
        return "not supported" in message or "unsupported parameter" in message

    def close(self) -> None:
        """Close the OpenAI client."""
        close_fn = getattr(self._client, "close", None)
        if callable(close_fn):
            close_fn()

    def __enter__(self) -> OpenAIResponseService:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        self.close()


__all__ = ["OpenAIResponseService", "OpenAIResponseError", "DEFAULT_OPENAI_BASE_URL"]
