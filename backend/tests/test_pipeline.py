import pytest

from app.pipeline import run_intent_pipeline
from app.schemas import ClassificationOutcome, IntentClassification


@pytest.mark.asyncio
async def test_pipeline_uses_local_fallback_without_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DEEPSEEK_API_KEY", "")

    response = await run_intent_pipeline("ML course er price koto?")

    assert response.intent == "course_pricing_payment"
    assert response.category == "relevant"
    assert response.source == "local"
    assert response.status == "success"
    assert response.routing_mode == "local_direct"
    assert response.local_score > 0
    assert response.matched_terms


@pytest.mark.asyncio
async def test_pipeline_gate_rejects_out_of_profile_intent(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_classifier(text: str, allowed_intents: set[str] | frozenset[str]) -> ClassificationOutcome:
        return ClassificationOutcome(
            result=IntentClassification(
                intent="bank_loan_application",
                confidence="high",
                reason="fake",
            ),
            source="ai",
            status="success",
        )

    monkeypatch.setattr("app.pipeline.classify_intent", fake_classifier)

    response = await run_intent_pipeline("I need a bank loan")

    assert response.intent == "unknown"
    assert response.category == "unknown"
    assert any(step.name == "Allowed-intent gate" and step.status == "rejected" for step in response.trace)


@pytest.mark.asyncio
async def test_pipeline_acknowledgement_becomes_neutral() -> None:
    response = await run_intent_pipeline("thanks")

    assert response.intent == "neutral"
    assert response.category == "neutral"
