from fastapi.testclient import TestClient

from app.core.config import settings


def test_list_public_legal_documents(client: TestClient) -> None:
    response = client.get(f"{settings.API_V1_STR}/public/legal-documents/")

    assert response.status_code == 200
    payload = response.json()
    assert (
        payload["simplified_notice"]
        == "Para crear tu cuenta, necesitas leer y aceptar la documentación legal aplicable. Puedes revisar cada documento en una nueva pestaña antes de continuar."
    )
    assert payload["documents"] == [
        {
            "type": "privacy_notice",
            "title": "Aviso de Privacidad",
            "url": "/privacy",
            "version": "v1.0",
            "required": True,
        },
        {
            "type": "terms_conditions",
            "title": "Términos y Condiciones",
            "url": "/terms-conditions",
            "version": "v1.0",
            "required": True,
        },
    ]
