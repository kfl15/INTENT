"""Intent taxonomy and deterministic category derivation.

This module mirrors the key lesson from the class:
the model predicts only an intent. The backend derives category.
"""

from __future__ import annotations

from typing import Literal

Category = Literal["relevant", "neutral", "irrelevant", "unknown"]

COURSE_INFO_INTENTS: tuple[str, ...] = (
    "course_list",
    "course_details",
    "course_pricing_payment",
    "course_projects",
    "course_schedule_duration",
    "career_certificate_outcomes",
)

FIT_ELIGIBILITY_INTENTS: tuple[str, ...] = (
    "prerequisite_fit",
    "beginner_friendliness",
    "background_fit",
    "career_guidance",
)

SUPPORT_ACTION_INTENTS: tuple[str, ...] = (
    "demo_trial_counseling",
    "enrollment_admission",
    "student_support_redirect",
    "instructor_info",
    "recording_access",
    "missed_class_recovery",
)

SYSTEM_STATE_INTENTS: tuple[str, ...] = (
    "neutral",
    "irrelevant",
    "unknown",
)

INTENTS: tuple[str, ...] = (
    *COURSE_INFO_INTENTS,
    *FIT_ELIGIBILITY_INTENTS,
    *SUPPORT_ACTION_INTENTS,
    *SYSTEM_STATE_INTENTS,
)

INTENT_TO_CATEGORY: dict[str, Category] = {
    **{intent: "relevant" for intent in COURSE_INFO_INTENTS},
    **{intent: "relevant" for intent in FIT_ELIGIBILITY_INTENTS},
    **{intent: "relevant" for intent in SUPPORT_ACTION_INTENTS},
    "neutral": "neutral",
    "irrelevant": "irrelevant",
    "unknown": "unknown",
}


def category_for_intent(intent: str) -> Category:
    """Return category by dictionary lookup, never by model prediction."""

    return INTENT_TO_CATEGORY.get(intent, "unknown")
