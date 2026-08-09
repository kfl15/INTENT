from app.overrides import apply_post_classification_overrides
from app.profiles import EDTECH_PROFILE
from app.schemas import ClassificationOutcome, IntentClassification


def _outcome(intent: str) -> ClassificationOutcome:
    return ClassificationOutcome(
        result=IntentClassification(intent=intent, confidence="medium", reason="test"),
        source="local",
        status="success",
    )


def test_acknowledgement_override_forces_neutral() -> None:
    outcome, steps = apply_post_classification_overrides(
        text="thanks",
        outcome=_outcome("course_details"),
        profile=EDTECH_PROFILE,
        dialogue_act="acknowledgement",
    )

    assert outcome.result.intent == "neutral"
    assert steps[0].status == "overridden"


def test_course_list_override_forces_course_list() -> None:
    outcome, steps = apply_post_classification_overrides(
        text="ki ki course available?",
        outcome=_outcome("unknown"),
        profile=EDTECH_PROFILE,
        dialogue_act=None,
    )

    assert outcome.result.intent == "course_list"
    assert any(step.status == "overridden" for step in steps)


def test_decision_support_override_forces_career_guidance() -> None:
    outcome, steps = apply_post_classification_overrides(
        text="ami confused, kon course nibo?",
        outcome=_outcome("unknown"),
        profile=EDTECH_PROFILE,
        dialogue_act=None,
    )

    assert outcome.result.intent == "career_guidance"
    assert any(step.name == "Override: decision support" and step.status == "overridden" for step in steps)
