from dataclasses import asdict
from types import SimpleNamespace
from typing import Any

import httpx
import pytest
from openai import APIStatusError, OpenAIError

from app.features.openai.models import build_openai_request_template_record
from app.features.openai.repository import OpenAIRequestTemplateRepository
from app.features.openai.schemas import OpenAIRequestTemplateCatalogResponse
from app.features.openai.service import OpenAIService
from app.features.openai.types import base as base_module
from app.features.openai.types.base import OpenAIResponseError, OpenAIResponseService


class FakeStreamContext:
    def __init__(self, events: list[Any]) -> None:
        self.events = events

    def __enter__(self) -> "FakeStreamContext":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        return None

    def __iter__(self):
        return iter(self.events)


class FakeResponses:
    def __init__(
        self,
        *,
        create_actions: list[Any] | None = None,
        stream_actions: list[Any] | None = None,
    ) -> None:
        self.create_calls: list[dict[str, Any]] = []
        self.stream_calls: list[dict[str, Any]] = []
        self.create_actions = create_actions or [
            {"output": [{"content": [{"text": " generated text "}]}]}
        ]
        self.stream_actions = stream_actions or [
            [
                SimpleNamespace(type="response.output_text.delta", delta="one"),
                SimpleNamespace(type="ignored", delta="ignored"),
                SimpleNamespace(type="response.output_text.delta", delta="two"),
            ]
        ]

    def _next_action(self, actions: list[Any]) -> Any:
        return actions.pop(0) if len(actions) > 1 else actions[0]

    def create(self, **kwargs: Any) -> Any:
        self.create_calls.append(kwargs)
        action = self._next_action(self.create_actions)
        if isinstance(action, BaseException):
            raise action
        return action

    def stream(self, **kwargs: Any) -> FakeStreamContext:
        self.stream_calls.append(kwargs)
        action = self._next_action(self.stream_actions)
        if isinstance(action, BaseException):
            raise action
        if isinstance(action, FakeStreamContext):
            return action
        return FakeStreamContext(action)


class FakeOpenAIClient:
    def __init__(self, responses: FakeResponses | None = None) -> None:
        self.responses = responses or FakeResponses()
        self.closed = False

    def close(self) -> None:
        self.closed = True


class FakeModelDump:
    def __init__(self, payload: dict[str, Any], *, accepts_mode: bool = True) -> None:
        self.payload = payload
        self.accepts_mode = accepts_mode

    def model_dump(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        if not self.accepts_mode and kwargs:
            raise TypeError("mode is not supported")
        del args, kwargs
        return self.payload


class FakeOpenAIError(OpenAIError):
    pass


class ExplodingModelDump:
    def model_dump(self, **kwargs: Any) -> dict[str, Any]:
        del kwargs
        raise RuntimeError("dump failed")


class FakeTextResponse:
    def __init__(self, value: Any, *, json_error: Exception | None = None) -> None:
        self.value = value
        self.json_error = json_error or ValueError("not json")

    def json(self) -> Any:
        raise self.json_error

    def text(self) -> Any:
        return self.value


class UnstringableResponse:
    def json(self) -> Any:
        raise ValueError("not json")

    @property
    def text(self) -> None:
        return None

    def __str__(self) -> str:
        raise RuntimeError("cannot stringify")


def make_api_status_error(status_code: int, payload_or_text: Any) -> APIStatusError:
    request = httpx.Request("POST", "https://api.openai.test/v1/responses")
    if isinstance(payload_or_text, dict):
        response = httpx.Response(status_code, json=payload_or_text, request=request)
    else:
        response = httpx.Response(
            status_code,
            text=str(payload_or_text),
            request=request,
        )
    return APIStatusError(
        "OpenAI request failed", response=response, body=payload_or_text
    )


def temperature_unsupported_error() -> APIStatusError:
    return make_api_status_error(
        400,
        {
            "error": {
                "message": "Unsupported parameter: temperature is not supported.",
                "type": "invalid_request_error",
                "code": "unsupported_parameter",
                "param": "temperature",
            }
        },
    )


class FakeDispatchResponseService:
    instances: list["FakeDispatchResponseService"] = []

    def __init__(self, **kwargs: Any) -> None:
        self.kwargs = kwargs
        self.closed = False
        self.calls: list[dict[str, Any]] = []
        self.__class__.instances.append(self)

    def __enter__(self) -> "FakeDispatchResponseService":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    def close(self) -> None:
        self.closed = True

    def create_response(self, **kwargs: Any) -> str:
        self.calls.append(kwargs)
        return "ok"

    def stream_response(self, **kwargs: Any):
        self.calls.append(kwargs)
        yield "ok"


def test_create_response_builds_input_and_extracts_nested_text() -> None:
    # Arrange
    client = FakeOpenAIClient()
    service = OpenAIResponseService(client=client, default_model="model-a")

    # Act
    text = service.create_response(
        "hello",
        system_prompt="system",
        temperature=0.1,
        max_output_tokens=50,
        metadata={"source": "test"},
    )

    # Assert
    assert text == "generated text"
    assert client.responses.create_calls == [
        {
            "model": "model-a",
            "input": [
                {"role": "system", "content": "system"},
                {"role": "user", "content": "hello"},
            ],
            "temperature": 0.1,
            "max_output_tokens": 50,
            "metadata": {"source": "test"},
        }
    ]


def test_response_service_init_without_client_or_api_key_raises() -> None:
    # Arrange / Act / Assert
    with pytest.raises(ValueError, match="Either api_key or preconfigured client"):
        OpenAIResponseService(api_key=None, client=None)


def test_response_service_init_builds_openai_client_kwargs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Arrange
    created_kwargs: dict[str, Any] = {}

    class RecordingOpenAIClient(FakeOpenAIClient):
        def __init__(self, **kwargs: Any) -> None:
            created_kwargs.update(kwargs)
            super().__init__()

    monkeypatch.setattr(base_module, "OpenAI", RecordingOpenAIClient)

    # Act
    service = OpenAIResponseService(
        api_key="sk-test",
        base_url="https://api.openai.test/v1/",
        organization="org-test",
        project="proj-test",
        timeout=12,
        max_retries=1,
    )

    # Assert
    assert isinstance(service._client, RecordingOpenAIClient)
    assert created_kwargs == {
        "api_key": "sk-test",
        "base_url": "https://api.openai.test/v1",
        "organization": "org-test",
        "project": "proj-test",
        "timeout": 12,
        "max_retries": 1,
    }


def test_create_response_replaces_existing_system_message() -> None:
    # Arrange
    client = FakeOpenAIClient()
    service = OpenAIResponseService(client=client, default_model="model-a")

    # Act
    service.create_response(
        [
            {"role": "system", "content": "old system"},
            {"role": "user", "content": "hello"},
        ],
        system_prompt="new system",
    )

    # Assert
    assert client.responses.create_calls[0]["input"] == [
        {"role": "system", "content": "new system"},
        {"role": "user", "content": "hello"},
    ]


def test_create_response_extracts_direct_output_text_and_object_text() -> None:
    # Arrange
    client = FakeOpenAIClient(
        FakeResponses(
            create_actions=[
                SimpleNamespace(output_text=" direct text "),
                SimpleNamespace(
                    output=[
                        SimpleNamespace(text=" output object text "),
                        SimpleNamespace(
                            content=[SimpleNamespace(text=" content object text ")]
                        ),
                    ]
                ),
                SimpleNamespace(
                    output=[
                        SimpleNamespace(text=""),
                        SimpleNamespace(
                            content=[SimpleNamespace(text=" content object text ")]
                        ),
                    ]
                ),
            ]
        )
    )
    service = OpenAIResponseService(client=client, default_model="model-a")

    # Act
    direct_text = service.create_response("hello")
    output_text = service.create_response("hello")
    content_text = service.create_response("hello")

    # Assert
    assert direct_text == "direct text"
    assert output_text == "output object text"
    assert content_text == "content object text"


def test_create_response_extracts_mapping_and_model_dump_shapes() -> None:
    # Arrange
    nested_object = SimpleNamespace(text={"value": " nested object text "})
    client = FakeOpenAIClient(
        FakeResponses(
            create_actions=[
                {"output_text": 42},
                {"output": [{"content": [{"text": ["hello", " ", "world"]}]}]},
                {"output": [{"content": [nested_object]}]},
                FakeModelDump({"content": {"text": " dumped text "}}),
                FakeModelDump({"text": " fallback dumped text "}, accepts_mode=False),
            ]
        )
    )
    service = OpenAIResponseService(client=client, default_model="model-a")

    # Act
    numeric_text = service.create_response("hello")
    list_text = service.create_response("hello")
    nested_text = service.create_response("hello")
    dumped_text = service.create_response("hello")
    fallback_dumped_text = service.create_response("hello")

    # Assert
    assert numeric_text == "42"
    assert list_text == "helloworld"
    assert nested_text == "nested object text"
    assert dumped_text == "dumped text"
    assert fallback_dumped_text == "fallback dumped text"


def test_create_response_empty_response_returns_empty_string() -> None:
    # Arrange
    client = FakeOpenAIClient(
        FakeResponses(create_actions=[SimpleNamespace(output=[])])
    )
    service = OpenAIResponseService(client=client, default_model="model-a")

    # Act
    result = service.create_response("hello")

    # Assert
    assert result == ""


def test_create_response_temperature_unsupported_retries_without_temperature() -> None:
    # Arrange
    responses = FakeResponses(
        create_actions=[
            temperature_unsupported_error(),
            {"output_text": "retried"},
        ]
    )
    client = FakeOpenAIClient(responses)
    service = OpenAIResponseService(client=client, default_model="model-a")

    # Act
    result = service.create_response("hello", temperature=0.7)

    # Assert
    assert result == "retried"
    assert responses.create_calls[0]["temperature"] == 0.7
    assert "temperature" not in responses.create_calls[1]


def test_create_response_temperature_retry_failure_raises_openai_response_error() -> (
    None
):
    # Arrange
    retry_error = make_api_status_error(
        429,
        {
            "error": {
                "message": "Rate limited",
                "type": "rate_limit_error",
                "code": "rate_limit_exceeded",
                "param": "model",
            }
        },
    )
    responses = FakeResponses(
        create_actions=[
            temperature_unsupported_error(),
            retry_error,
        ]
    )
    service = OpenAIResponseService(
        client=FakeOpenAIClient(responses),
        default_model="model-a",
    )

    # Act / Assert
    with pytest.raises(OpenAIResponseError) as exc_info:
        service.create_response("hello", temperature=0.7)

    error = exc_info.value
    assert error.status_code == 429
    assert str(error) == "Rate limited"
    assert error.error_type == "rate_limit_error"
    assert error.error_code == "rate_limit_exceeded"
    assert error.error_param == "model"
    assert error.raw["error"]["message"] == "Rate limited"


def test_create_response_openai_error_wraps_raw_response() -> None:
    # Arrange
    raw_response = httpx.Response(
        500,
        json={"error": "network"},
        request=httpx.Request("POST", "https://api.openai.test/v1/responses"),
    )
    error = FakeOpenAIError("network failed")
    error.response = raw_response
    service = OpenAIResponseService(
        client=FakeOpenAIClient(FakeResponses(create_actions=[error])),
        default_model="model-a",
    )

    # Act / Assert
    with pytest.raises(OpenAIResponseError) as exc_info:
        service.create_response("hello")

    assert exc_info.value.status_code == 500
    assert str(exc_info.value) == "OpenAI client error: network failed"
    assert exc_info.value.raw == {"error": "network"}


def test_create_response_invalid_prompt_raises_value_error() -> None:
    service = OpenAIResponseService(client=FakeOpenAIClient())

    with pytest.raises(ValueError, match="Prompt must be string"):
        service.create_response([{"role": "user"}])  # type: ignore[list-item]


def test_response_service_validate_model_without_default_or_input_raises_value_error() -> (
    None
):
    # Arrange
    service = OpenAIResponseService(client=FakeOpenAIClient(), default_model="")

    # Act / Assert
    with pytest.raises(ValueError, match="model must be specified"):
        service.create_response("hello", model=None)


def test_response_service_build_input_invalid_prompt_raises_value_error() -> None:
    # Arrange
    service = OpenAIResponseService(client=FakeOpenAIClient(), default_model="model-a")

    # Act / Assert
    with pytest.raises(ValueError, match="Prompt must be string"):
        service._build_input(("tuple",))  # type: ignore[arg-type]


def test_response_service_extract_output_text_handles_mapping_content_and_output_list() -> (
    None
):
    # Arrange
    service = OpenAIResponseService(client=FakeOpenAIClient(), default_model="model-a")

    # Act / Assert
    assert service._extract_output_text({"content": {"value": " mapped "}}) == "mapped"
    assert service._extract_output_text({"output": [{"text": " from output "}]}) == (
        "from output"
    )
    assert service._extract_output_text({"output": [False]}) == "False"


def test_response_service_extract_output_text_model_dump_exception_returns_empty_string() -> (
    None
):
    # Arrange
    service = OpenAIResponseService(client=FakeOpenAIClient(), default_model="model-a")

    # Act
    result = service._extract_output_text(ExplodingModelDump())

    # Assert
    assert result == ""


def test_response_service_parse_error_response_non_string_fields_preserves_raw() -> (
    None
):
    # Arrange
    service = OpenAIResponseService(client=FakeOpenAIClient(), default_model="model-a")
    error = make_api_status_error(
        400,
        {"error": {"message": 123, "type": 456, "code": 789, "param": False}},
    )

    # Act
    parsed = service._parse_error_response(error)

    # Assert
    assert parsed["status_code"] == 400
    assert parsed["message"] == "123"
    assert parsed["raw"]["error"]["message"] == 123
    assert "error_type" not in parsed
    assert "error_code" not in parsed
    assert "error_param" not in parsed


def test_response_service_parse_error_response_plain_text_sets_raw_response() -> None:
    # Arrange
    service = OpenAIResponseService(client=FakeOpenAIClient(), default_model="model-a")
    error = make_api_status_error(500, "plain failure")

    # Act
    parsed = service._parse_error_response(error)

    # Assert
    assert parsed["status_code"] == 500
    assert parsed["raw"] == {"raw_response": "plain failure"}


def test_response_service_get_raw_response_handles_json_string_text_callable_and_str_fallback() -> (
    None
):
    # Arrange
    json_string_error = FakeOpenAIError("json string")
    json_string_error.response = httpx.Response(
        500,
        json="raw string",
        request=httpx.Request("POST", "https://api.openai.test/v1/responses"),
    )
    text_callable_error = FakeOpenAIError("text callable")
    text_callable_error.response = FakeTextResponse({"error": "from text"})
    text_scalar_error = FakeOpenAIError("text scalar")
    text_scalar_error.response = FakeTextResponse(123)
    unstringable_error = FakeOpenAIError("unstringable")
    unstringable_error.response = UnstringableResponse()

    # Act / Assert
    assert OpenAIResponseService._get_raw_response(json_string_error) == "raw string"
    assert OpenAIResponseService._get_raw_response(text_callable_error) == {
        "error": "from text"
    }
    assert OpenAIResponseService._get_raw_response(text_scalar_error) == "123"
    assert OpenAIResponseService._get_raw_response(unstringable_error) is None


def test_response_service_wrap_raw_payload_handles_none_mapping_and_string() -> None:
    # Act / Assert
    assert OpenAIResponseService._wrap_raw_payload(None) is None
    assert OpenAIResponseService._wrap_raw_payload({"error": "raw"}) == {"error": "raw"}
    assert OpenAIResponseService._wrap_raw_payload("raw text") == {
        "raw_response": "raw text"
    }


def test_response_service_close_calls_client_close_when_available() -> None:
    # Arrange
    client = FakeOpenAIClient()
    service = OpenAIResponseService(client=client, default_model="model-a")

    # Act
    service.close()

    # Assert
    assert client.closed is True


def test_response_service_context_manager_closes_client() -> None:
    # Arrange
    client = FakeOpenAIClient()

    # Act
    with OpenAIResponseService(client=client, default_model="model-a") as service:
        assert service._client is client

    # Assert
    assert client.closed is True


def test_stream_response_yields_deltas_and_invokes_callback() -> None:
    # Arrange
    client = FakeOpenAIClient()
    service = OpenAIResponseService(client=client, default_model="model-a")
    deltas: list[str] = []

    # Act
    result = list(service.stream_response("hello", on_delta=deltas.append))

    # Assert
    assert result == ["one", "two"]
    assert deltas == ["one", "two"]
    assert client.responses.stream_calls[0]["input"] == [
        {"role": "user", "content": "hello"}
    ]


def test_stream_response_temperature_unsupported_retries_without_temperature() -> None:
    # Arrange
    responses = FakeResponses(
        stream_actions=[
            temperature_unsupported_error(),
            [
                SimpleNamespace(type="response.output_text.delta", delta="retry"),
                SimpleNamespace(type="ignored", delta="ignored"),
            ],
        ]
    )
    client = FakeOpenAIClient(responses)
    service = OpenAIResponseService(client=client, default_model="model-a")
    deltas: list[str] = []

    # Act
    result = list(
        service.stream_response("hello", temperature=0.3, on_delta=deltas.append)
    )

    # Assert
    assert result == ["retry"]
    assert deltas == ["retry"]
    assert responses.stream_calls[0]["temperature"] == 0.3
    assert "temperature" not in responses.stream_calls[1]


def test_stream_response_ignores_non_delta_events_and_calls_on_delta() -> None:
    # Arrange
    responses = FakeResponses(
        stream_actions=[
            [
                SimpleNamespace(type="ignored", delta="skip"),
                SimpleNamespace(type="response.output_text.delta", delta="one"),
                SimpleNamespace(type="response.completed", delta="skip"),
            ]
        ]
    )
    service = OpenAIResponseService(
        client=FakeOpenAIClient(responses),
        default_model="model-a",
    )
    deltas: list[str] = []

    # Act
    result = list(service.stream_response("hello", on_delta=deltas.append))

    # Assert
    assert result == ["one"]
    assert deltas == ["one"]


def test_stream_response_temperature_retry_failure_raises_openai_response_error() -> (
    None
):
    # Arrange
    responses = FakeResponses(
        stream_actions=[
            temperature_unsupported_error(),
            make_api_status_error(
                429,
                {
                    "error": {
                        "message": "Retry stream failed",
                        "type": "rate_limit_error",
                        "code": "rate_limit_exceeded",
                        "param": "model",
                    }
                },
            ),
        ]
    )
    service = OpenAIResponseService(
        client=FakeOpenAIClient(responses),
        default_model="model-a",
    )

    # Act / Assert
    with pytest.raises(OpenAIResponseError) as exc_info:
        list(service.stream_response("hello", temperature=0.3))

    assert exc_info.value.status_code == 429
    assert str(exc_info.value) == "Retry stream failed"
    assert exc_info.value.error_code == "rate_limit_exceeded"
    assert "temperature" not in responses.stream_calls[1]


def test_stream_response_api_status_error_raises_openai_response_error() -> None:
    # Arrange
    service = OpenAIResponseService(
        client=FakeOpenAIClient(
            FakeResponses(
                stream_actions=[
                    make_api_status_error(
                        400,
                        {
                            "error": {
                                "message": "Bad request",
                                "type": "invalid_request_error",
                                "code": "bad_request",
                                "param": "input",
                            }
                        },
                    )
                ]
            )
        ),
        default_model="model-a",
    )

    # Act / Assert
    with pytest.raises(OpenAIResponseError) as exc_info:
        list(service.stream_response("hello"))

    assert exc_info.value.status_code == 400
    assert str(exc_info.value) == "Bad request"
    assert exc_info.value.error_code == "bad_request"
    assert exc_info.value.error_param == "input"


def test_openai_service_execute_dispatches_and_closes_response_service() -> None:
    # Arrange
    FakeDispatchResponseService.instances = []
    service = OpenAIService(
        api_key="sk-test",
        default_model="model-a",
        response_service_factory=FakeDispatchResponseService,
        unused=None,
    )

    # Act
    result = service.execute(
        "create_response",
        function_kwargs={"prompt": "hello"},
        service_overrides={"default_model": "model-b", "project": None},
    )

    # Assert
    instance = FakeDispatchResponseService.instances[0]
    assert result == "ok"
    assert instance.kwargs["default_model"] == "model-b"
    assert "unused" not in instance.kwargs
    assert "project" not in instance.kwargs
    assert instance.calls == [{"prompt": "hello"}]
    assert instance.closed is True


def test_openai_service_rejects_unsupported_option() -> None:
    service = OpenAIService(
        api_key="sk-test",
        response_service_factory=FakeDispatchResponseService,
    )

    with pytest.raises(ValueError, match="Unsupported option"):
        service.execute("unknown")


def test_openai_template_repository_returns_serializable_records() -> None:
    # Arrange
    repository = OpenAIRequestTemplateRepository()

    # Act
    records = repository.list_template_records()
    response = OpenAIRequestTemplateCatalogResponse(
        items=[asdict(record) for record in records]
    )
    campaign_template = repository.get_template("reputation_campaign_strategy")
    campaign_record = build_openai_request_template_record(
        "reputation_campaign_strategy",
        campaign_template,
    )

    # Assert
    assert "reputation_campaign_strategy" in repository.list_template_names()
    assert response.items
    assert campaign_record.name == "reputation_campaign_strategy"
    assert campaign_record.has_system_prompt is True
    assert campaign_record.has_text_schema is True
