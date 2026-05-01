from fastapi.testclient import TestClient

from tests.contract.helpers import (
    assert_operation,
    assert_schema_has_properties,
    get_openapi_schema,
)


def test_instagram_data_openapi_contract_exposes_expected_paths_and_shapes(
    client: TestClient,
) -> None:
    # Arrange
    schema = get_openapi_schema(client)

    # Act / Assert
    for resource in [
        "ig-credentials",
        "ig-profiles",
        "ig-posts",
        "ig-reels",
        "ig-metrics",
        "ig-profile-snapshots",
    ]:
        assert_operation(
            schema, path=f"/api/v1/{resource}/", method="post", success_status="201"
        )
        assert_operation(schema, path=f"/api/v1/{resource}/", method="get")

    assert_operation(
        schema, path="/api/v1/ig-profiles/by-username/{username}", method="get"
    )
    assert_operation(schema, path="/api/v1/ig-profiles/by-usernames", method="post")
    assert_operation(schema, path="/api/v1/ig-profile-snapshots/advanced", method="get")

    assert_schema_has_properties(
        schema, "IgCredentialPublic", {"_id", "login_username"}
    )
    assert_schema_has_properties(
        schema, "Profile", {"_id", "username", "follower_count"}
    )
    assert_schema_has_properties(
        schema, "PostsDocument", {"_id", "profile_id", "posts"}
    )
    assert_schema_has_properties(
        schema, "ReelsDocument", {"_id", "profile_id", "reels"}
    )
    assert_schema_has_properties(
        schema, "Metrics", {"_id", "post_metrics", "reel_metrics"}
    )
