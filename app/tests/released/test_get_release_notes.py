from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_get_relevant_endpoint():
    response = client.get("/api/v1/released/get-relevant-notes?major=1&minor=2&keywords=keyword1,keyword2")
    assert response.status_code == 200
    assert response.json() == {"release": {"major": 1, "minor": 2}, "paragraphs": []}
