import pytest

from app.classifier import classify_intent
from app.config import get_settings
from app.profiles import EDTECH_PROFILE
from app.schemas import IntentClassification


@pytest.mark.asyncio
async def test_classifier_uses_local_direct_for_obvious_message_without_api_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DEEPSEEK_API_KEY", "")
    get_settings.cache_clear()

    outcome = await classify_intent("class kobe start hobe?", EDTECH_PROFILE.all_intents)

    assert outcome.source == "local"
    assert outcome.status == "success"
    assert outcome.routing_mode == "local_direct"
    assert outcome.result.intent == "course_schedule_duration"

    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_classifier_calls_ai_when_local_score_is_weak(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
    get_settings.cache_clear()

    async def fake_llm(
        text: str,
        allowed_intents: set[str] | frozenset[str],
    ) -> IntentClassification:
        return IntentClassification(
            intent="course_details",
            confidence="high",
            reason="AI matched general course question.",
        )

    monkeypatch.setattr("app.classifier.classify_intent_with_llm", fake_llm)

    outcome = await classify_intent("tell me more about NLP", EDTECH_PROFILE.all_intents)

    assert outcome.source == "ai"
    assert outcome.status == "success"
    assert outcome.routing_mode == "ai"
    assert outcome.result.intent == "course_details"


@pytest.mark.asyncio
async def test_classifier_uses_fallback_when_ai_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
    monkeypatch.setenv("LOCAL_DIRECT_MIN_SCORE", "999")
    get_settings.cache_clear()

    async def failing_llm(
        text: str,
        allowed_intents: set[str] | frozenset[str],
    ) -> IntentClassification:
        raise RuntimeError("provider down")

    monkeypatch.setattr("app.classifier.classify_intent_with_llm", failing_llm)

    outcome = await classify_intent("course fee koto?", EDTECH_PROFILE.all_intents)

    assert outcome.source == "local"
    assert outcome.status == "fallback"
    assert outcome.routing_mode == "ai_fallback"
    assert outcome.result.intent == "course_pricing_payment"


@pytest.mark.asyncio
async def test_classifier_returns_failed_when_ai_fails_and_fallback_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
    monkeypatch.setenv("LOCAL_DIRECT_MIN_SCORE", "999")
    monkeypatch.setenv("INTENT_FALLBACK_ENABLED", "false")
    get_settings.cache_clear()

    async def failing_llm(
        text: str,
        allowed_intents: set[str] | frozenset[str],
    ) -> IntentClassification:
        raise RuntimeError("provider down")

    monkeypatch.setattr("app.classifier.classify_intent_with_llm", failing_llm)

    outcome = await classify_intent("course fee koto?", EDTECH_PROFILE.all_intents)

    assert outcome.source == "ai"
    assert outcome.status == "failed"
    assert outcome.routing_mode == "ai_failed"
    assert outcome.result.intent == "unknown"


@pytest.mark.asyncio
async def test_classifier_marks_repeated_message_cache_hit() -> None:
    first = await classify_intent("course fee koto?", EDTECH_PROFILE.all_intents)
    second = await classify_intent("course fee koto?", EDTECH_PROFILE.all_intents)

    assert first.cache_hit is False
    assert second.cache_hit is True
