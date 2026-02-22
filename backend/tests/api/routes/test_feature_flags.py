from fastapi.testclient import TestClient
from sqlmodel import Session

from app import crud_admin
from app.core.config import settings
from tests.utils.utils import random_email, random_lower_string


def _create_internal_admin_token_headers(
    *, client: TestClient, db: Session, role_code: str
) -> dict[str, str]:
    email = random_email()
    password = random_lower_string()
    role = crud_admin.get_admin_role_by_code(session=db, code=role_code)
    assert role
    crud_admin.create_admin_user(session=db, email=email, password=password, role=role)
    login_data = {"username": email, "password": password}
    response = client.post(
        f"{settings.API_V1_STR}/internal/login/access-token",
        data=login_data,
    )
    assert response.status_code == 200
    access_token = response.json()["access_token"]
    return {"Authorization": f"Bearer {access_token}"}


def test_feature_flag_crud_and_audit_as_superuser(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    key = f"ff-{random_lower_string()[:10]}"
    create_payload = {
        "key": key,
        "description": "Test feature flag",
        "is_enabled": False,
        "is_public": True,
    }
    create_response = client.post(
        f"{settings.API_V1_STR}/internal/feature-flags/",
        headers=superuser_token_headers,
        json=create_payload,
    )
    assert create_response.status_code == 200
    assert create_response.json()["key"] == key
    assert create_response.json()["is_enabled"] is False
    assert create_response.json()["is_public"] is True

    patch_payload = {"is_enabled": True}
    patch_response = client.patch(
        f"{settings.API_V1_STR}/internal/feature-flags/{key}",
        headers=superuser_token_headers,
        json=patch_payload,
    )
    assert patch_response.status_code == 200
    assert patch_response.json()["is_enabled"] is True

    audit_response = client.get(
        f"{settings.API_V1_STR}/internal/feature-flags/{key}/audit",
        headers=superuser_token_headers,
    )
    assert audit_response.status_code == 200
    assert audit_response.json()["count"] >= 2
    assert audit_response.json()["data"][0]["action"] == "updated"

    delete_response = client.delete(
        f"{settings.API_V1_STR}/internal/feature-flags/{key}",
        headers=superuser_token_headers,
    )
    assert delete_response.status_code == 200
    assert delete_response.json()["message"] == "Feature flag deleted successfully"

    audit_after_delete_response = client.get(
        f"{settings.API_V1_STR}/internal/feature-flags/{key}/audit",
        headers=superuser_token_headers,
    )
    assert audit_after_delete_response.status_code == 200
    assert audit_after_delete_response.json()["data"][0]["action"] == "deleted"


def test_public_feature_flags_only_returns_public(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    public_key = f"ff-public-{random_lower_string()[:8]}"
    private_key = f"ff-private-{random_lower_string()[:8]}"

    public_payload = {
        "key": public_key,
        "description": "Public FF",
        "is_enabled": True,
        "is_public": True,
    }
    private_payload = {
        "key": private_key,
        "description": "Private FF",
        "is_enabled": True,
        "is_public": False,
    }
    create_public_response = client.post(
        f"{settings.API_V1_STR}/internal/feature-flags/",
        headers=superuser_token_headers,
        json=public_payload,
    )
    assert create_public_response.status_code == 200

    create_private_response = client.post(
        f"{settings.API_V1_STR}/internal/feature-flags/",
        headers=superuser_token_headers,
        json=private_payload,
    )
    assert create_private_response.status_code == 200

    public_list_response = client.get(f"{settings.API_V1_STR}/public/feature-flags/")
    assert public_list_response.status_code == 200
    public_keys = {item["key"] for item in public_list_response.json()["data"]}
    assert public_key in public_keys
    assert private_key not in public_keys

    private_single_response = client.get(
        f"{settings.API_V1_STR}/public/feature-flags/{private_key}"
    )
    assert private_single_response.status_code == 404


def test_viewer_admin_can_read_but_cannot_write_feature_flags(
    client: TestClient, db: Session
) -> None:
    viewer_headers = _create_internal_admin_token_headers(
        client=client, db=db, role_code="viewer"
    )

    list_response = client.get(
        f"{settings.API_V1_STR}/internal/feature-flags/",
        headers=viewer_headers,
    )
    assert list_response.status_code == 200

    create_payload = {
        "key": f"ff-viewer-{random_lower_string()[:8]}",
        "description": "Viewer write attempt",
        "is_enabled": False,
        "is_public": False,
    }
    create_response = client.post(
        f"{settings.API_V1_STR}/internal/feature-flags/",
        headers=viewer_headers,
        json=create_payload,
    )
    assert create_response.status_code == 403
