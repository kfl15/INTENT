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
    assert body["routing_mode"] in {"local_direct", "ai", "ai_fallback", "ai_failed"}
    assert isinstance(body["cache_hit"], bool)
    assert isinstance(body["local_score"], int | float)
    assert isinstance(body["matched_terms"], list)
    assert len(body["trace"]) >= 6


def test_evaluate_intents_endpoint() -> None:
    response = client.get("/evaluate-intents")

    body = response.json()
    assert response.status_code == 200
    assert body["total_cases"] >= 1
    assert 0 <= body["accuracy"] <= 1
