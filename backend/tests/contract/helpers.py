from typing import Any

from fastapi.testclient import TestClient

OpenAPI = dict[str, Any]


def get_openapi_schema(client: TestClient) -> OpenAPI:
    response = client.get("/api/v1/openapi.json")
    assert response.status_code == 200
    return response.json()


def assert_operation(
    schema: OpenAPI,
    *,
    path: str,
    method: str,
    success_status: str = "200",
) -> dict[str, Any]:
    operation = schema["paths"][path][method.lower()]
    assert success_status in operation["responses"]
    return operation


def assert_schema_has_properties(
    schema: OpenAPI,
    component: str,
    expected_properties: set[str],
) -> None:
    properties = schema["components"]["schemas"][component]["properties"]
    assert expected_properties <= set(properties)
