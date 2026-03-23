from fastapi.testclient import TestClient

from services.document_service.app.main import app

client = TestClient(app)


def test_health_endpoint_exposes_service_metadata() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["service"] == "document-service"
    assert payload["status"] == "ok"
    assert payload["version"]


def test_swagger_ui_is_exposed_on_required_path() -> None:
    response = client.get("/ui-swagger")

    assert response.status_code == 200
    assert "Simbir.Health Document Service" in response.text
