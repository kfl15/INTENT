import pytest

from app.classifier import classify_intent
from app.config import get_settings
from app.profiles import EDTECH_PROFILE


@pytest.mark.asyncio
async def test_classifier_falls_back_when_no_deepseek_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DEEPSEEK_API_KEY", "")
    get_settings.cache_clear()

    outcome = await classify_intent("class kobe start hobe?", EDTECH_PROFILE.all_intents)

    assert outcome.source == "local"
    assert outcome.status == "fallback"
    assert outcome.result.intent == "course_schedule_duration"

    get_settings.cache_clear()
