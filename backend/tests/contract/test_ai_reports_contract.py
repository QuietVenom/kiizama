from fastapi.testclient import TestClient

from tests.contract.helpers import (
    assert_operation,
    assert_schema_has_properties,
    get_openapi_schema,
)


def test_ai_reports_openapi_contract_exposes_expected_paths_and_shapes(
    client: TestClient,
) -> None:
    # Arrange
    schema = get_openapi_schema(client)

    # Act / Assert
    assert_operation(schema, path="/api/v1/openai/instagram", method="post")
    profiles_operation = assert_operation(
        schema, path="/api/v1/brand-intelligence/profiles-existence", method="get"
    )
    campaign_operation = assert_operation(
        schema,
        path="/api/v1/brand-intelligence/reputation-campaign-strategy",
        method="post",
    )
    creator_operation = assert_operation(
        schema,
        path="/api/v1/brand-intelligence/reputation-creator-strategy",
        method="post",
    )
    social_report_operation = assert_operation(
        schema, path="/api/v1/social-media-report/instagram", method="post"
    )

    assert_schema_has_properties(schema, "InstagramAIResponse", {"results"})
    assert_schema_has_properties(schema, "ProfileExistenceCollection", {"profiles"})
    assert_schema_has_properties(schema, "InstagramReportRequest", {"usernames"})

    assert profiles_operation["responses"]["200"]["content"]["application/json"]
    report_content_types = {"text/html", "application/pdf", "application/zip"}
    assert report_content_types <= set(
        campaign_operation["responses"]["200"]["content"]
    )
    assert report_content_types <= set(creator_operation["responses"]["200"]["content"])
    assert report_content_types <= set(
        social_report_operation["responses"]["200"]["content"]
    )
