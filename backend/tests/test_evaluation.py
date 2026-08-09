import pytest

from app.evaluation import evaluate_intents


@pytest.mark.asyncio
async def test_evaluation_metrics_calculate() -> None:
    response = await evaluate_intents()

    assert response.total_cases >= 1
    assert 0 <= response.accuracy <= 1
    assert response.details
    assert "course_pricing_payment" in response.per_intent
