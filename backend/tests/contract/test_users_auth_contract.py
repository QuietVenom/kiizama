from fastapi.testclient import TestClient

from tests.contract.helpers import (
    assert_operation,
    assert_schema_has_properties,
    get_openapi_schema,
)


def test_users_auth_openapi_contract_exposes_expected_paths_and_shapes(
    client: TestClient,
) -> None:
    # Arrange
    schema = get_openapi_schema(client)

    # Act / Assert
    for method, path, status_code in [
        ("get", "/api/v1/users/", "200"),
        ("post", "/api/v1/users/", "200"),
        ("patch", "/api/v1/users/me", "200"),
        ("patch", "/api/v1/users/me/password", "200"),
        ("get", "/api/v1/users/me", "200"),
        ("delete", "/api/v1/users/me", "200"),
        ("post", "/api/v1/users/signup", "200"),
        ("get", "/api/v1/users/{user_id}", "200"),
        ("patch", "/api/v1/users/{user_id}", "200"),
        ("put", "/api/v1/users/{user_id}/access-profile", "200"),
        ("delete", "/api/v1/users/{user_id}", "200"),
        ("post", "/api/v1/login/access-token", "200"),
        ("post", "/api/v1/login/test-token", "200"),
        ("post", "/api/v1/password-recovery/{email}", "200"),
        ("post", "/api/v1/reset-password/", "200"),
        ("post", "/api/v1/internal/login/access-token", "200"),
        ("post", "/api/v1/internal/login/test-token", "200"),
        ("post", "/api/v1/private/users/", "200"),
        ("post", "/api/v1/utils/test-email/", "201"),
    ]:
        assert_operation(schema, path=path, method=method, success_status=status_code)

    assert_schema_has_properties(schema, "UserPublic", {"id", "email", "full_name"})
    assert_schema_has_properties(
        schema,
        "AdminUserPublic",
        {"id", "email", "access_profile", "plan_status", "billing_eligible"},
    )
    assert_schema_has_properties(schema, "Token", {"access_token", "token_type"})
