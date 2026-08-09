from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_health() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_classify_endpoint() -> None:
    response = client.post("/classify", json={"text": "recording pabo?"})

    body = response.json()
    assert response.status_code == 200
    assert body["intent"] == "recording_access"
    assert body["category"] == "relevant"
    assert len(body["trace"]) >= 6
