from fastapi.testclient import TestClient

from tests.contract.helpers import (
    assert_operation,
    assert_schema_has_properties,
    get_openapi_schema,
)


def test_billing_public_infra_openapi_contract_exposes_expected_paths_and_shapes(
    client: TestClient,
) -> None:
    # Arrange
    schema = get_openapi_schema(client)

    # Act / Assert
    for method, path in [
        ("get", "/api/v1/billing/me"),
        ("get", "/api/v1/billing/notices"),
        ("post", "/api/v1/billing/checkout-session"),
        ("post", "/api/v1/billing/portal-session"),
        ("post", "/api/v1/billing/notices/{notice_id}/read"),
        ("post", "/api/v1/billing/notices/{notice_id}/dismiss"),
        ("post", "/api/v1/billing/webhooks/stripe"),
        ("get", "/api/v1/internal/feature-flags/"),
        ("post", "/api/v1/internal/feature-flags/"),
        ("patch", "/api/v1/internal/feature-flags/{flag_key}"),
        ("delete", "/api/v1/internal/feature-flags/{flag_key}"),
        ("get", "/api/v1/public/feature-flags/"),
        ("get", "/api/v1/public/legal-documents/"),
        ("post", "/api/v1/public/waiting-list/"),
        ("get", "/api/v1/health/live"),
        ("get", "/api/v1/health/ready"),
        ("get", "/api/v1/health-check/"),
        ("get", "/api/v1/health-check/deep"),
        ("get", "/api/v1/events/stream"),
    ]:
        assert_operation(schema, path=path, method=method)

    assert_schema_has_properties(
        schema,
        "BillingSummaryPublic",
        {"access_profile", "features", "notices", "plan_status"},
    )
    assert_schema_has_properties(schema, "FeatureFlagPublic", {"key", "is_enabled"})
    assert_schema_has_properties(schema, "PublicLegalDocuments", {"documents"})
