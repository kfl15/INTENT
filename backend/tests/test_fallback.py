from app.fallback import local_fallback_outcome
from app.profiles import EDTECH_PROFILE


def test_local_fallback_detects_pricing() -> None:
    outcome = local_fallback_outcome(
        "ML course er price koto?",
        "test",
        EDTECH_PROFILE.all_intents,
    )

    assert outcome.result.intent == "course_pricing_payment"
    assert outcome.source == "local"


def test_local_fallback_detects_single_word_token() -> None:
    outcome = local_fallback_outcome(
        "course fee koto?",
        "test",
        EDTECH_PROFILE.all_intents,
    )

    assert outcome.result.intent == "course_pricing_payment"
    assert "Matched local keyword" in outcome.result.reason


def test_local_fallback_detects_phrase_keyword() -> None:
    outcome = local_fallback_outcome(
        "class kobe start hobe?",
        "test",
        EDTECH_PROFILE.all_intents,
    )

    assert outcome.result.intent == "course_schedule_duration"


def test_local_fallback_respects_allowed_intents() -> None:
    outcome = local_fallback_outcome(
        "recording pabo?",
        "test",
        {"course_pricing_payment", "unknown"},
    )

    assert outcome.result.intent == "unknown"
