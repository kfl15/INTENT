"""Business logic overrides that run after classification."""

from __future__ import annotations

from app.profiles import BusinessTypeProfile
from app.schemas import ClassificationOutcome, IntentClassification, PipelineStep

# Detect explicit course list request
def is_explicit_course_list_request(text: str) -> bool:
    normalized = text.lower()
    phrases = (
        "course list",
        "all course",
        "all courses",
        "ki ki course",
        "available course",
        "catalog",
    )
    return any(phrase in normalized for phrase in phrases)

# Detect confused/decision-support message
def has_decision_support_signal(text: str) -> bool:
    normalized = text.lower()
    phrases = (
        "confused",
        "hesitant",
        "not sure",
        "which course",
        "kon course",
        "suggest",
    )
    return any(phrase in normalized for phrase in phrases)

# Apply all override rules. Classifier predicts intent first. Then override rules may change the intent.
def apply_post_classification_overrides(
    text: str,
    outcome: ClassificationOutcome,
    profile: BusinessTypeProfile,
    dialogue_act: str | None,
) -> tuple[ClassificationOutcome, list[PipelineStep]]:
    steps: list[PipelineStep] = []

    if dialogue_act == "acknowledgement" and "neutral" in profile.all_intents:
        outcome = outcome.model_copy(
            update={
                "result": IntentClassification(
                    intent="neutral",
                    confidence="high",
                    reason="Acknowledgement dialogue act.",
                )
            }
        )
        steps.append(
            PipelineStep(
                name="Override: acknowledgement",
                status="overridden",
                detail="Acknowledgement forced final intent to neutral.",
            )
        )
    else:
        steps.append(
            PipelineStep(
                name="Override: acknowledgement",
                status="skipped",
                detail="No acknowledgement override applied.",
            )
        )

    if is_explicit_course_list_request(text) and outcome.result.intent in {
        "course_list",
        "career_guidance",
        "neutral",
        "unknown",
    }:
        outcome = outcome.model_copy(
            update={
                "result": IntentClassification(
                    intent="course_list",
                    confidence="high",
                    reason="Explicit catalog request.",
                )
            }
        )
        steps.append(
            PipelineStep(
                name="Override: explicit course list",
                status="overridden",
                detail="Explicit catalog request forced course_list.",
            )
        )
    else:
        steps.append(
            PipelineStep(
                name="Override: explicit course list",
                status="skipped",
                detail="No catalog override applied.",
            )
        )

    if has_decision_support_signal(text) and outcome.result.intent in {
        "neutral",
        "unknown",
    }:
        outcome = outcome.model_copy(
            update={
                "result": IntentClassification(
                    intent="career_guidance",
                    confidence="high",
                    reason="Customer requested decision support.",
                )
            }
        )
        steps.append(
            PipelineStep(
                name="Override: decision support",
                status="overridden",
                detail="Confused or hesitant signal forced career_guidance.",
            )
        )
    else:
        steps.append(
            PipelineStep(
                name="Override: decision support",
                status="skipped",
                detail="No decision-support override applied.",
            )
        )

    return outcome, steps
