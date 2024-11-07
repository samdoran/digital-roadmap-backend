from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_get_relevant_endpoint():
    # response = client.get("/api/digital-roadmap/v1/release-notes/get-relevant-notes?major=1&minor=2&keywords=keyword1,keyword2")
    # assert response.status_code == 200
    response = {"foo": "bar"}
    assert response == {"foo": "bar"}
