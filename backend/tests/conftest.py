import pytest

from app.classifier import clear_classification_cache
from app.config import get_settings


@pytest.fixture(autouse=True)
def clear_settings_cache(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DEEPSEEK_API_KEY", "")
    monkeypatch.setenv("CLASSIFICATION_STRATEGY", "smart_hybrid")
    monkeypatch.setenv("LOCAL_DIRECT_MIN_SCORE", "2.0")
    monkeypatch.setenv("INTENT_FALLBACK_ENABLED", "true")
    monkeypatch.setenv("CACHE_TTL_SECONDS", "300")
    monkeypatch.setenv("REQUEST_LOG_PATH", "logs/test_intent_requests.jsonl")
    get_settings.cache_clear()
    clear_classification_cache()
    yield
    get_settings.cache_clear()
    clear_classification_cache()
