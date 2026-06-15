from fastapi.testclient import TestClient

from tests.contract.helpers import (
    assert_operation,
    assert_schema_has_properties,
    get_openapi_schema,
)


def _request_schema_properties(
    schema: dict,
    *,
    path: str,
    method: str,
) -> set[str]:
    operation = schema["paths"][path][method.lower()]
    request_schema = operation["requestBody"]["content"]["application/json"]["schema"]
    ref = request_schema["$ref"].split("/")[-1]
    return set(schema["components"]["schemas"][ref]["properties"])


def test_ig_scraper_openapi_contract_exposes_expected_paths_and_shapes(
    client: TestClient,
) -> None:
    # Arrange
    schema = get_openapi_schema(client)

    # Act / Assert
    for path, status_code in [
        ("/api/v1/ig-scraper/jobs", "202"),
        ("/api/v1/ig-scraper/jobs/apify", "202"),
    ]:
        assert_operation(schema, path=path, method="post", success_status=status_code)

    assert_operation(schema, path="/api/v1/ig-scraper/jobs/{job_id}", method="get")
    assert_operation(
        schema, path="/api/v1/ig-scraper/profiles/apify-batch", method="post"
    )
    assert_operation(
        schema, path="/api/v1/internal/ig-scraper/jobs/{job_id}/complete", method="post"
    )
    assert "/api/v1/ig-scraper/profiles/batch" not in schema["paths"]
    assert "/api/v1/ig-scraper/profiles/recommendations" not in schema["paths"]
    for path in (
        "/api/v1/ig-scraper/jobs",
        "/api/v1/ig-scraper/jobs/apify",
        "/api/v1/ig-scraper/profiles/apify-batch",
    ):
        assert _request_schema_properties(schema, path=path, method="post") == {
            "usernames"
        }

    assert_schema_has_properties(
        schema, "InstagramScrapeJobCreateResponse", {"job_id", "status"}
    )
    assert_schema_has_properties(
        schema, "InstagramScrapeJobStatusResponse", {"job_id", "status"}
    )
